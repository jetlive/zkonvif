# coding: utf-8
import json
import thread, time
import urllib,urllib2,sys,io
from CardServer import livingS, ReslivingS
from RecordingCommand import RecordingCommand
from Check_CardLive import CardLive_Runing


sys.path.append('../')
from common.utils import zkutils
from common.uty_log import log
from common.conf_mc import getconf_mulcast

# 全局配置
global_conf = {
	"NSService": {
		"sip" : "172.16.30.251",
		"sport" :"8080" 
	}
}

gcs = getconf_mulcast()

try:
    conf = json.loads(gcs)
    global_conf = conf
except:
    pass


def log_info(info):
    log(log, project='recording')

def StartLiving(ip,mac,hosttype):
    log('StartLiving calling, ip=%s, mac=%s, hosttype=%s' % (ip, mac, hosttype), project = 'recording', level = 3)
    rc = {}
    rc['result'] = 'ok'
    rc['info'] = ''
    rc = _rtmp_living(ip, mac, hosttype)
    return rc


def _x86_rtmp_living_data(mac):
    data = {}
    mac = mac.lower()
    data['group_id'] = mac
    move = {}
    move['uid'] = mac + '_movie'

    resource1 = {}
    resource1['uid'] = mac + '_teacher'
    resource2 = {}
    resource2['uid'] = mac + '_student'
    resource3 = {}
    resource3['uid'] = mac + '_vga'
    resource4 = {}
    resource4['uid'] = mac + '_teacher_full'
    resource5 = {}
    resource5['uid'] = mac + '_student_full'
    resource6 = {}
    resource6['uid'] = mac + '_blackboard_writing'
    data['uids'] = [resource1,resource2,resource3]#保留三路资源
    return data

def _arm_rtmp_living_data(ip, mac, hosttype):
    data = {}
    mac = mac.lower()
    data['group_id'] = mac
    movie = {}
    movie['uid'] = mac + '_movie'

    resource1 = {}
    resource1['uid'] = mac + '_teacher'
    resource2 = {}
    resource2['uid'] = mac + '_student'
    resource3 = {}
    resource3['uid'] = mac + '_vga'
    resource4 = {}
    resource4['uid'] = mac + '_teacher_full'
    resource5 = {}
    resource5['uid'] = mac + '_student_full'
    resource6 = {}
    resource6['uid'] = mac + '_blackboard_writing'
    
    livingMode = 'Resource'
    #_rcmd = RecordingCommand()
    #info = _rcmd.send_command('RecordCmd=QueryRAllInfo', ip)
    #if 'livingMode=All' in info['info']:
        #livingMode = 'All'
    #elif 'livingMode=Movie' in info['info']:
        #livingMode = 'Movie'

    if hosttype == 'D3100':
        #if livingMode == 'Recource':
            #data['uids'] = [resource2, resource3, resource5, resource1]
        #elif livingMode == 'All':
        data['uids'] = [resource2, resource3, resource5, resource1, movie]
        #elif livingMode == 'Movie':
            #data['uids'] = [movie]
    elif hosttype == 'D3101':
        data['uids'] = [recource2, resource3, movie]
    elif hosttype == 'D31020':
        data['uids'] = [resource1, recource2, resource3]
    elif hosttype == 'D31021' or hosttype == 'D3103':
        data['uids'] == [resource3, resource1, resource2]
    elif hosttype == 'D3104':
        data['uids'] == [resource1, resource2, resource5, resource4, resource3]
     
    return data


def _load_base_url():
    '''
    平台地址
    '''
    ret = global_conf
    r = ret['NSService']
    if ' ' in r['sip'] or ' ' in r['sport']:
        raise Exception("include ' '")
    if r['sip'] == '' or r['sport'] == '':
        raise Exception("include''")
    return 'http://%s:%s/deviceService/'%(r['sip'],r['sport'])


def _error_code(code,content):
    rc = {}
    rc['result'] = 'ok'
    rc['info'] = ''
    if code == 101:
        rc['result'] = 'error'
        rc['info'] = 'NOT_SUPPORTED_METHOD'
        return rc
    elif code == 102:
        rc['result'] = 'error'
        rc['info'] = 'NO_PARAMETER'
        return rc
    elif code == 103:
        rc['result'] = 'error'
        rc['info'] = 'INVALID_PARMAMETER'
        return rc
    elif code  == 110:
        rc['result'] = 'error'
        rc['info'] = 'DB_ERROR'
        return rc
    elif code == 120:
        rc['result'] = 'error'
        rc['info'] = 'NO_VALID_SERVERS'
        return rc
    elif code == 150:
        rc['result'] = 'error'
        rc['info'] = 'SOCKET_ERROR'
        return rc
    elif code == 200:
        rc['result'] = 'error'
        rc['info'] = 'UNKNOWN_ERROR'
        return rc
    elif code == 122:
        rc['result'] = 'ok'
        urls = []
        urls = content['content']
        infos = []

        for url in urls:
            info = {}
            info['uid'] = str(url['stream_uid'])
            info['rtmp_repeater'] = str(url['publish_url'])
            if 'teacher' in url['stream_uid']:
                info['card_info'] = 'card0'
            if 'teacher_full' in url['stream_uid']:   
                info['card_info'] = 'card1'
            if 'student' in url['stream_uid']:
                info['card_info'] = 'card2'
            if 'student_full' in url['stream_uid']:               
                info['card_info'] = 'card3'
            if 'vga' in url['stream_uid']: 
                info['card_info'] = 'card4'
            if 'blackboard_writing' in url['stream_uid']:
                info['card_info'] = 'card5'
            if 'movie' in url['stream_uid']:   
                info['card_info'] = 'card6'
            str(info)
            infos.append(info)
        rc['info'] = infos
        return rc
    elif code == 120:
        rc['result'] = 'error'
        rc['info'] = 'all servers are shutdown or full,please check'
        return rc
    else:
        rc['result'] = 'error'        
        rc['info'] = 'UNKNOWN_ERROR'
        return rc        


def _rtmp_living(ip, mac, hosttype):
    rc = {}
    rc['result'] = 'ok'
    rc['info'] = ''

    log('_rtmp_living: starting ...., ip=%s, mac=%s, hosttype=%s' % (ip, mac, hosttype), \
            project = 'recording')

    if hosttype == 'x86':
        if not CardLive_Runing():
            log('_rtmp_living: cardlive.exe NOT prepared?', project='recording', level = 2)
            rc['result'] = 'error'
            rc['info'] = 'cardlive.exe is not exit!'
            return rc

    try:
        log('_rtmp_living: try to get relay url', project = 'recording')
        middle_req = urllib2.urlopen(_load_base_url() + 'getServerUrl?type=middle', timeout = 2)
        middle_url = middle_req.read()
    except Exception as e:
        log('_rtmp_living: to get relay url fault! reason=%s' % e, project = 'recording', level = 1)
        rc['result'] = 'error'
        rc['info'] = str(e)
        return rc


    log('_rtmp_living: en, got relay url: %s' % middle_url, project = 'recording')

    try:
        log('_rtmp_living: to call relay of prepublishbatch', project = 'recording')
        req = urllib2.Request(middle_url+'/repeater/prepublishbatch')
        if hosttype == 'x86':
            data = _x86_rtmp_living_data(mac)
        else:
            data = _arm_rtmp_living_data(ip, mac, hosttype)
        data = json.dumps(data)

        response = urllib2.urlopen(req, data)
        content = json.load(response)

        log('_rtmp_living: response_code=%s' % str(content['response_code']), project = 'recording')    

        if content['response_code'] != 0:
            rc = _error_code(content['response_code'],content)
            log('_rtmp_living: err: info=%s' % rc['info'], project = 'recording', level = 1)
            return rc

        urls = []
        urls = content['content']
        movie_url = rtmp_ip = port = app = ''
        infos = []

        for url in urls:
            info = {}
            info['uid'] = str(url['uid'])
            info['rtmp_repeater'] = str(url['rtmp_repeater'])
            if 'teacher' in url['uid']:
                info['card_info'] = 'card0'
            if 'teacher_full' in url['uid']:   
                info['card_info'] = 'card1'
            if 'student' in url['uid']:
                info['card_info'] = 'card2'
            if 'student_full' in url['uid']:               
                info['card_info'] = 'card3'
            if 'vga' in url['uid']: 
                info['card_info'] = 'card4'
            if 'blackboard_writing' in url['uid']:
                info['card_info'] = 'card5'
            if 'movie' in url['uid']:   
                info['card_info'] = 'card6'

            str(info)

            infos.append(info)

            if 'teacher' in url['rtmp_repeater']:
                #movie_url = url['rtmp_repeater']
                #livingS(movie_url)
                url = url['rtmp_repeater']
                url = url[7:]
                rtmp_ip = url.split(':')[0]
                url = url[len(rtmp_ip)+1:]
                port = url.split('/')[0]
                url =url[len(port)+1:]
                app = url.split('/')[0]

        _rcmd = RecordingCommand()
        if hosttype == 'x86':
            ReslivingS(rtmp_ip,port,app)
        else:
            arm_arg = 'BroadCastCmd=RtmpUrlS&'
            for info in infos:
                arm_arg = arm_arg + info['rtmp_repeater'] +'^'
            arm_arg = arm_arg[:-1]
            log_info(arm_arg)
            rc = _rcmd.send_command(arm_arg,ip)
            print rc

        time.sleep(1)
        rc=_rcmd.send_command('BroadCastCmd=StartBroadCast',ip)

        if rc['result'] == 'ok':
            rc['info'] = infos

    except Exception as err:
        rc['result'] = 'error'
        rc['info'] = str(err)
        log('_rtmp_living: exception info=%s' % rc['info'], \
                project = 'recording', level = 1)

    return rc


def StopLiving():
    log('StopLiving called', project = 'recording', level = 3)
    _rcmd = RecordingCommand()
    rc=_rcmd.send_command('BroadCastCmd=StopBroadCast',ip)
    return rc

