#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'syuson'

import asyncio,os,inspect,logging,functools

from urllib import parse

from aiohttp import web

from apis import APIError

def get(path):
	'''Define decorator @get('/path')'''
	def decorator(func):
		@functools.wraps(func)
		def warpper(*args,**kw):
			return func(*args,**kw)
		warpper.__method__ = 'GET'
		warpper.__route__ = path
		return warpper
	return decorator

def post(path):
	'''Define decorator @post('/path')'''
	def decorator(func):
		@functools.wraps(func)
		def warpper(*args,**kw):
			return func(*args,**kw)
		warpper.__method__ = 'POST'
		warpper.__route__ = path
		return warpper
	return decorator


# 引用inspect模块，创建几个函数以获取URL处理函数与request参数之间的关系
# 收集没有默认值的命名关键字参数
def get_required_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)
	return tuple(args)

#获取命名关键字参数
def get_named_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY :
			args.append(name)
	return tuple(args)

#判断有没有明明关键字参数
def has_named_kw_args(fn):
	params = inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY :
			return True

#判断有没有关键字参数
def has_var_kw_arg(fn):
	params = inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD :
			return True

#判断是否含有叫request的参数，且该参数是否为最后一个参数
def has_request_arg(fn):
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name,param in params.items():
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function:%s%s' % (fn.__name__,str(sig)))
	return found

#从URL函数中分析需要接收的参数，从request中获取必要的参数、调用URL函数，然后把结果转换为web.Response
class RequestHandler(object):
	"""docstring for RequestHandler"""
	def __init__(self, app, fn):
		self.app = app
		self._func = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	#实现直接在实例本身上调用
	async def __call__(self,request):
		kw = None
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
			if request.method == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest(text='Missing content_type')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = await request.json()
					if not isinstance(params,dict):
						return web.HTTPBadRequest(text='Json body mmust be object')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = await request.post()
					kw = dict(**params)
				else:
					return web.HTTPBadRequest(text = 'Unsupported content_type:%s' % request.content_type)
			if request == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k,v in parse.parse_qs(qs,True).items():
						kw[k] = v[0]
		if kw is None:
			kw = dict(**request.match_info)
		else:
			# 当函数参数没有关键字参数时，剔除request除去命名关键字参数所有的参数信息
			if not self._has_var_kw_arg and  self._named_kw_args:
				#remove all unamed kw
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			#check named arg
			for k,v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args:%s' % k)
				kw[k] = v
		if self._has_request_arg:
			kw['request'] = request
		#check required kw
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest(text='Missing argument : %s' % name)
		logging.info('call with args:%s' % str(kw))
		try:
			r = await self._func(**kw)
			return r
		except APIError as e:
			raise dict(error=e.error,data=e.data,message=e.message)

#添加静态文件夹的路径
def add_static(app):
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
	app.router.add_static('/static/',path)
	logging.info('add sttaic %s => %s' %('/static/',path))

#编写函数用来注册一个URL处理函数
def add_route(app,fn):
	method = getattr(fn,'__method__',None)
	path = getattr(fn,'__route__',None)
	if path is None or method is None:
		return ValueError('@get or @post not defined in %s' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method,path,fn.__name__,','.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method,path,RequestHandler(app,fn))

#批量注册URL函数
def add_routes(app,module_name):
	n = module_name.rfind('.')
	if n == (-1):
		mod =  __import__(module_name,globals(),locals())
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n],globals(),locals(),[name]),name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod,attr)
		if callable(fn):
			method = getattr(fn,'__method__',None)
			path = getattr(fn,'__route__',None)
			if method and path:
				add_route(app,fn)



		