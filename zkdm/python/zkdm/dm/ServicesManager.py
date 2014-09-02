# coding: utf-8

import LocalConfig
import subprocess, shlex
import threading, time
import sys, re

sys.path.append('../')
from common.utils import zkutils


# 本地配置文件
FNAME = 'config.json'


class ServicesManager:
	''' 本地服务管理
		包括：
		  	启动/停止服务，
			使能/禁用服务
			返回服务列表 ...
		
		FIXME: title 不需要，显示名字放在平台端 ...
		XXX: 是否启动工作线程，轮询服务状态？..
		XXX: 如果服务已经启动了，怎么办？..
	'''
	def __init__(self):
		u = zkutils()
		self.__ip = u.myip()			# 可能是交换机映射后的 ip
		self.__ip_real = u.myip_real()
		self.__activated = [] # (p, sd)
		self.__start_all_enabled()


	def list_services(self):
		''' 返回所有服务列表, 并且将服务的 url 中的 ip 部分，换成自己的 ..
		'''
		ssd = LocalConfig.load_config(FNAME)
		ss = ssd['services']
		for s in ss:
			if 'url' in s:
				new_url = self.__fix_url(s['url'])
				s['url'] = new_url
		return ss


	def dump_activated(self):
		''' poll 状态 ...'''
		print '--- dump ---'
		for x in self.__activated:
			print '  ==> ', x[1]['name'], ': state:', x[0].poll()
		print '============'


	def close(self):
		''' 强制关闭所有启动的服务 ???? '''
		for x in self.__activated:
			print ' ==> to kill "', x[1]['name'], '"'
			x[0].kill()


	def start_service(self, name):
		''' 启动服务，如果 name 存在 '''
		ssd = self.list_services()
		for x in ssd:
			if x['name'] == name and x['enable']:
				self.__start_service(x)
				return True
		return False



	def stop_service(self, name):
		''' 停止服务 '''
		ssd = self.list_services()
		for x in ssd:
			if x['name'] == name:
			   self.__stop_service(x)
			   return True
		return False


	def __fix_url(self, url):
		''' 将 url 中的 ip 部分换成本机 ip
			在配置中，url 的格式为：
			  <protocol>://<ip>:<port>/path

			  如 http://<ip>:10001/event
			  需要就 <ip> 替换为本机实际 ip 地址
		'''
		return url.replace(r'<ip>', self.__ip)



	def __start_all_enabled(self):
		''' 启动所有允许的服务 ..
			返回启动的服务的数目 ..
		'''
		n = 0
		for sd in self.list_services():
			if sd['enable']:
				n += 1
				sr = self.__start_service(sd)
				if sr:
					self.__activated.append(sr)
		return n


	def __start_service(self, sd):
		''' 启动服务, 首先检查是否已经启动 ??. 

			总是使用 subprocess.Popen class ..
			TODO:  if !fork 直接启动 py 脚本？是否能在 arm 上节省点内存？ ..
		'''
		for s in self.__activated:
			if s[1]['name'] == sd['name']:
				return None # 已经启动 ..

		args = shlex.split(sd['path'])
		print ' ==> start', args
		p = subprocess.Popen(args)
		print '        pid:', p.pid
		return (p, sd)
		

	def __stop_service(self, sd):
		''' 停止服务
		'''
		for s in self.__activated:
			if s[1]['name'] == sd['name']:
				s[0].kill()
				self.__activated.remove(s)
				break


	def enable_service(self, name, en = True):
		''' 使能/禁用服务 '''
		ssd = LocalConfig.load_config(FNAME)
		for s in ssd['services']:
			if s['name'] == name:
			   s['enable'] = en
			   break
		LocalConfig.save_config(FNAME, ssd)



if __name__ == '__main__':
	sm = ServicesManager()
	all = sm.list_services()
	print all
	count = 10
	while count > 0:
		count -= 1
		time.sleep(1.0)
		sm.dump_activated()
	sm.enable_service('event service', True)
	sm.close()