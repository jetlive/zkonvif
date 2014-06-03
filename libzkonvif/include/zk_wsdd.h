/** zonekey onvif lib

  	zk_wsdd: 提供统一的设备发现，声明接口
 */

#pragma once

#ifndef __cplusplus
extern "C" {
#endif // c++

	typedef struct zk_wsdd_target_t zk_wsdd_target_t;
	typedef struct zk_wsdd_client_t zk_wsdd_client_t;

	struct zk_wsdd_TargetDesc
	{
		const char *type; // 目前支持 'eval', 'ptz'
		const char *url;	// 服务访问 url ...
	};

	zk_wsdd_target_t *zk_wsdd_target_open(const struct zk_wsdd_TargetDesc *desc);
	void zk_wsdd_target_close(zk_wsdd_target_t *target);

#ifndef __cplusplus
}
#endif // c++

