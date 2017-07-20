#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'syuson'

import asyncio
from coroweb import get,post

#编写用于测试的URL处理函数
@get('/')
async def handler_url_blog(request):
    body='<h1>Awesome</h1>'
    return body
@get('/greeting')
async def handler_url_greeting(*,name,request):
    body='<h1>Awesome: /greeting %s</h1>'%name
    return body