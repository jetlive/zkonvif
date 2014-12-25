# coding: utf-8
# @file: uty_token.py
# @date: 2014-12-24
# @brief:
# @detail: 用于描述需要注册的主机，服务信息，并提供“被代理”主机/服务的查询
#
#################################################################

import os, json, io, sys

TOKEN_FNAME = "tokens.json"

def __valid_host(h):
    ''' 必须存在 mac, ip, hosttype '''
    if 'mac' in h and 'ip' in h and 'hosttype' in h:
        return True
    else:
        return False

def __load(fname = None):
    if fname is None:
        fname = TOKEN_FNAME

    f = io.open(fname, encoding='utf-8')
    j = json.loads(f.read())
    f.close()
    return j


def gather_hds(fname = None):
    ''' 根据 tokens.json 文件收集并构建 host description list '''
    j = __load(fname)
    hds = []
    for i in j:
        h = j[i]
        if __valid_host(h):
            hd = {}
            hd['mac'] = h['mac']
            hd['ip'] = h['ip']
            hd['type'] = h['hosttype']
            hds.append(hd)
    return hds

def gather_sds(service_type = None, fname = None):
    ''' 收集sevice_type 指定的服务信息，并构建 service description list
    '''
    j = __load(fname)
    sds = []
    for i in j:
        h = j[i]  # host
        if __valid_host(h) and 'services' in h:
            for sk in h['services']:
                st = h['services'][sk] # type
                if service_type is not None and service_type != sk:
                    continue
                for sid in st:
                    s = st[sid]    # id
                    sd = {}
                    if 'url' in s:
                        sd['id'] = sid
                        sd['mac'] = h['mac']
                        sd['ip'] = h['ip']
                        sd['url'] = s['url']
                        sd['type'] = sk
                        sds.append(sd)
    return sds


def get_private_from_token(token, service_id, tokens):
    j = tokens
    for i in j:
        h = j[i]
        if __valid_host(h) and 'services' in h:
            for sk in h['services']:
                st = h['services'][sk] # type
                for sid in st:
                    s = st[sid]    # id
                    private = s['private']
                    return private
    return {}

def get_private(token, service_id, fname = None):
    ''' 从 fname 的 token 表中取出 token + serviceid 对应的 private 数据字典'''
    j = __load(fname)
    return get_private_from_token(token, service_id, j)



if __name__ == '__main__':
    import reght, time
    reght.verbose = True

    p = get_private('1', 'CARD02')
    print p

    sys.exit()

    hds = gather_hds()
    rh = reght.RegHost(hds)  # 主机注册

    sds = gather_sds('ptz')
    rs = reght.RegHt(sds)  # 服务注册

    time.sleep(60000)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

