#!/usr/bin/python
# coding: utf-8
# 
# @file: reg_dm.py
# @date: 2015-02-07
# @brief:
# @detail:
#
#################################################################

import sys, time, os
sys.path.append('../')
from common.utils import zkutils
from common.reght import RegHt
from common.reght import RegHost
import common.reght
from common.uty_token import *
import portalocker

try:
    os.remove('reght.log')
except:
    pass

pid_fname = "reg_dm.id"
p = open(pid_fname, 'w')
try:
    portalocker.lock(p, portalocker.LOCK_EX | portalocker.LOCK_NB)
except:
    print 'ERR: only one instance can be started!!!'
    sys.exit()

service_url = "http://<ip>:10000/dm"
local = {'type': 'dm', 'id': 'dm', 'url': service_url}
sds = gather_sds('dm', '../common/tokens.json')
sds.append(local)

#common.reght.verbose = True
rh = RegHt(sds)

while True:
    time.sleep(10.0)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

