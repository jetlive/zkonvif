#include "MyEvent.h"
#include "../../common/utils.h"
#include "../../common/log.h"
#include "../../common/KVConfig.h"

MyEvent::MyEvent(int port)
{
	char buf[64];
	port_ = port;

	// 注意使用了 https !
	snprintf(buf, sizeof(buf), "https://%s:%d", util_get_myip(), port_);
	url_ = buf;

	start();
}

MyEvent::~MyEvent()
{
}

void MyEvent::run()
{
	KVConfig cfg("event.config");	// 事件服务配置 ..

#ifdef WITH_OPENSSL
	if (soap_ssl_server_context(soap, SOAP_SSL_DEFAULT, cfg.get_value("server-key", "server.pem"), 0, cfg.get_value("ca-cert", 0), 0, 0, 0, 0)) {
		log(LOG_FAULT, "%s: soap_ssl_server_context failure!\n", __func__);
		soap_print_fault(stderr);
		::exit(-1);
	}
#endif
	if (soap_valid_socket(this->soap->master) || soap_valid_socket(bind(NULL, port_, 100))) {
		for ( ; ; ) {
			if (!soap_valid_socket(accept())) {
				log(LOG_ERROR, "%s: soap_accept err??\n", __func__);
				continue;
			}

#ifdef WITH_OPENSSL
			if (soap_ssl_accept(soap)) {
				log(LOG_ERROR, "%s: soap_ssl_accept err???\n", __func__);
				soap_print_fault(stderr);
			}
			else {
				serve();
			}
#else
			serve();
#endif
			destroy();
		}
	}

	soap_done(soap);
}

void MyEvent::post(ServiceInf *service, int code, const char *info)
{
	// 将通知发送到匹配的 PullPoint ...
	// XXX: 这里将 ns() == "*" 作为全匹配 .
	ost::MutexLock al(cs_pull_points_);
	PULLPOINTS::iterator it;
	for (it = pull_points_.begin(); it != pull_points_.end(); ++it) {
		const char *ns = ((ServiceInf*)(*it))->ns();
		if (!strcmp(ns, "*") || !strcmp(service->ns(), ns)) {
			(*it)->append(code, info);
		}
	}

	/** 删除“死亡列表”中的所有对象 .. 
	 */
	for (it = death_list_.begin(); it != death_list_.end(); ++it) {
		delete (*it);
	}

	death_list_.clear();
}

int MyEvent::GetServiceCapabilities(_tev__GetServiceCapabilities *tev__GetServiceCapabilities,
									_tev__GetServiceCapabilitiesResponse *tev__GetServiceCapabilitiesResponse)
{
	tev__GetServiceCapabilitiesResponse->Capabilities = soap_new_tev__Capabilities(soap);

	// 不支持 basic notification interface .
	tev__GetServiceCapabilitiesResponse->Capabilities->MaxNotificationProducers = (int*)soap_malloc(soap, sizeof(int));
	*tev__GetServiceCapabilitiesResponse->Capabilities->MaxNotificationProducers = 0;

	// 不支持 seeking
	tev__GetServiceCapabilitiesResponse->Capabilities->PersistentNotificationStorage = (bool*)soap_malloc(soap, sizeof(bool));
	*tev__GetServiceCapabilitiesResponse->Capabilities->PersistentNotificationStorage = false;

	tev__GetServiceCapabilitiesResponse->Capabilities->MaxPullPoints = 0;

	return SOAP_OK;
}

int MyEvent::GetEventProperties(_tev__GetEventProperties *tev__GetEventProperties,
								_tev__GetEventPropertiesResponse *tev__GetEventPropertiesResponse)
{
	return SOAP_OK;
}

int MyEvent::CreatePullPointSubscription(_tev__CreatePullPointSubscription *tev__CreatePullPointSubscription,
										 _tev__CreatePullPointSubscriptionResponse *tev__CreatePullPointSubscriptionResponse)
{
	/** 启动一个新的 socket，接收 PullMessageRequest, UnsubscribeRequest 等 */
	// FIXME: 应该支持 Filter ...
	// 这里假设没有设置 filter，则支持所有 ..
	MyPullPoint *pp = new MyPullPoint(this, "*");

	tev__CreatePullPointSubscriptionResponse->wsnt__CurrentTime = time(0);
	tev__CreatePullPointSubscriptionResponse->wsnt__TerminationTime = tev__CreatePullPointSubscriptionResponse->wsnt__CurrentTime + 365 * 24 * 60 * 60; // 呵呵，一年后结束 .
	tev__CreatePullPointSubscriptionResponse->SubscriptionReference.Address = soap_strdup(soap, pp->url());
	tev__CreatePullPointSubscriptionResponse->SubscriptionReference.ReferenceParameters = 0;
	tev__CreatePullPointSubscriptionResponse->SubscriptionReference.Metadata = 0;
	tev__CreatePullPointSubscriptionResponse->SubscriptionReference.__any = 0;
	tev__CreatePullPointSubscriptionResponse->SubscriptionReference.__size = 0;
	tev__CreatePullPointSubscriptionResponse->SubscriptionReference.__anyAttribute = 0;

	ost::MutexLock al(cs_pull_points_);
	pull_points_.push_back(pp);

	return SOAP_OK;
}

void MyPullPoint::run()
{
	log(LOG_DEBUG, "%s: oooh, PullPoint %s started\n", __func__, url_.c_str());

	/** 处理此连接点 ....
	*/
	while (!quit_) {
		if (!soap_valid_socket(accept())) {
			log(LOG_ERROR, "%s: accept err???\n", __func__);
			continue;
		}

		serve();
		destroy();
	}

	soap_done(soap);	// 对应着构造函数 ..
	evt_->remove_pullpoint(this); // 从 MyEvent 的队列中删除 ....

	log(LOG_DEBUG, "%s: ok, PullPoint %s terminated!\n", __func__, url_.c_str());
}

int MyPullPoint::PullMessages(_tev__PullMessages *tev__PullMessages, _tev__PullMessagesResponse *tev__PullMessagesResponse)
{
	log(LOG_DEBUG, "%s: calling ...\n", __func__);

	/** 直到 pending_message 有消息，才返回 ..

		FIXME: 没有处理 _tev__PullMessages 中的 MessageLimit ...
		*/

	int timeout = (int)tev__PullMessages->Timeout;  // XXX: 这个 Timeout 参数是什么单位？秒，分？ ..
	//		这里按照 秒 来算吧 :(

	bool t = false;
	std::vector<NotifyMessage> msgs;
	while (!curr_msgs(msgs)) {
		if (!sem_.wait(timeout * 1000)) {
			t = true;
			break;
		}
	}

	// FIXME: 如果超时，如果返回 Fault Message ???

	// response
	tev__PullMessagesResponse->CurrentTime = time(0);
	tev__PullMessagesResponse->TerminationTime = tev__PullMessagesResponse->CurrentTime + 365 * 24 * 60 * 60; // 呵呵，增加一年 .

	std::vector<NotifyMessage>::iterator it;
	for (it = msgs.begin(); it != msgs.end(); ++it) {
		/** XXX: 照理说，需要分清楚： When: 何时发生, Who: 谁的事件, What: 事件的内容 ....
				但看 onvif 文档和 ws-topics，看的一头雾水 ...
		 */
		wsnt__NotificationMessageHolderType *mht = soap_new_wsnt__NotificationMessageHolderType(soap);
		mht->Message.__any = soap_strdup(soap, it->desc());
	}

	return SOAP_OK;
}

int MyPullPoint::Unsubscribe(_wsnt__Unsubscribe *wsnt__Unsubscribe, _wsnt__UnsubscribeResponse *wsnt__UnsubscribeResponse)
{
	// XXX: 这里无需做啥工作，只需要通知线程下个循环退出即可 :)
	quit_ = true;
	log(LOG_DEBUG, "%s: calling ...\n", __func__);
	return SOAP_OK;
}

int MyPullPoint::append(int code, const char *info)
{
	ost::MutexLock al(cs_pending_messages);

	NotifyMessage nm;
	nm.code = code;
	nm.info = info;

	pending_messages.push_back(nm);
	sem_.post();

	return 0;
}