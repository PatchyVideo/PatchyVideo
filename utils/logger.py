
from db import db

import sys
import datetime
import threading
threadlocal = threading.local() 

from bson import ObjectId
from utils.crypto import random_bytes_str
from pymongo import WriteConcern
from functools import wraps

def beginEvent(endpoint, ip, path, args, obj = None) :
	setattr(threadlocal, 'event_op', endpoint)
	setattr(threadlocal, 'event_user', None)

	doc = {
		'time': datetime.datetime.now(),
		'level': 'MSG',
		'ip': ip,
		'endpoint': endpoint,
		'path': path,
		'args': args,
	}
	if obj and 'msg' in obj :
		doc['msg'] = obj['msg']
		del obj['msg']
	doc['obj'] = obj
	
	event_id = db.logs.insert_one(doc).inserted_id
	setattr(threadlocal, 'event_id', event_id)

	return ObjectId(event_id)

def setEventUser(user) :
	setattr(threadlocal, 'event_user', user)

def setEventUserAndID(user, event_id) :
	setattr(threadlocal, 'event_user', user)
	setattr(threadlocal, 'event_id', event_id)

def getEventID() :
	if hasattr(threadlocal, 'event_id') :
		return getattr(threadlocal, 'event_id')
	return ''

def setEventOp(op) :
	setattr(threadlocal, 'event_op', op)

def setEventID(event_id) :
	setattr(threadlocal, 'event_id', event_id)

def _ignore_error(func) :
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			ret = func(*args, **kwargs)
			return ret
		except Exception as ex:
			print(ex, file = sys.stderr)
		return None
	return wrapper

@_ignore_error
def log(op = '', level = "MSG", obj = None) :
	event_id = getEventID()
	event_op = getattr(threadlocal, 'event_op') or op
	event_user = getattr(threadlocal, 'event_user') or {'profile': {'username': '<anonymous>'}, '_id': ''}

	doc = {
		'time': datetime.datetime.now(),
		'level': level,
		'id': event_id,
		'op': event_op,
		'user': event_user['_id']
	}
	if obj and 'msg' in obj :
		doc['msg'] = obj['msg']
		del obj['msg']
	doc['obj'] = obj
	db.logs._insert(doc, write_concern = WriteConcern(w = 0))

@_ignore_error
def log_e(event_id, user, op = '', level = "MSG", obj = None) :
	doc = {
		'time': datetime.datetime.now(),
		'level': level,
		'id': event_id,
		'op': op,
		'user': user['_id']
	}
	if obj and 'msg' in obj :
		doc['msg'] = obj['msg']
		del obj['msg']
	doc['obj'] = obj
	db.logs._insert(doc, write_concern = WriteConcern(w = 0))

@_ignore_error
def log_ne(op = '', level = "MSG", obj = None) :
	doc = {
		'time': datetime.datetime.now(),
		'level': level,
		'op': op
	}
	if obj and 'msg' in obj :
		doc['msg'] = obj['msg']
		del obj['msg']
	doc['obj'] = obj
	db.logs._insert(doc, write_concern = WriteConcern(w = 0))

def _diff(old_tags, new_tags):
	old_tags_set = set(old_tags)
	new_tags_set = set(new_tags)
	added_tags = new_tags_set - old_tags_set
	removed_tags = (new_tags_set ^ old_tags_set) - added_tags
	return list(added_tags), list(removed_tags)
