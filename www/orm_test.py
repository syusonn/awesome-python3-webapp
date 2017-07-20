#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import orm
from user import User

__author__ = 'syuson'

async def connecDB(loop):
	username = 'root'
	password = 'root'
	dbname = 'pydb'
	await orm.create_pool(loop,user=username,password=password,db=dbname)

async def destoryDB():
	await orm.destory_pool()

async def test_findAll(loop):
	await connecDB(loop)
	userlist = await User.findAll(orderBy="name",limit=2)
	print('all user:%s' % userlist)
	await destoryDB()

async def test_findNumber(loop):
	await connecDB(loop)
	id = await User.findNumber('id')
	name = await User.findNumber('name')
	print('id:%s;name:%s' % (id,name))
	await destoryDB()

async def test_find(loop):
	await connecDB(loop)
	user = await User.find('123')
	print('user:%s' % user)
	await destoryDB()

async def test_save(loop):
	await connecDB(loop)
	user = await User.find('123')
	if user is None:
		user = User(id=123,name='syuson')
		await user.save()
	await destoryDB()

async def test_update(loop):
	await connecDB(loop)
	user = await User.find('123')
	if user is not None:
		user.name = 'zona'
		await user.update()
		print('user update:%s' % user)
	await destoryDB()

async def test_remove(loop):
	await connecDB(loop)
	user = await User.find('123')
	if user is not None:
		await user.remove()
		print('user remove:%s' % user)
	await destoryDB()

loop = asyncio.get_event_loop()

loop.run_until_complete(test_findAll(loop))
loop.run_until_complete(test_findNumber(loop))
loop.run_until_complete(test_find(loop))
loop.run_until_complete(test_save(loop))
loop.run_until_complete(test_update(loop))
loop.run_until_complete(test_remove(loop))

loop.close()