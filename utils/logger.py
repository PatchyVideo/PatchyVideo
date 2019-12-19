
from db import db

import sys
import datetime
import threading
threadlocal = threading.local() 

from utils.crypto import random_bytes_str

def beginEvent(endpoint, path, obj = None) :
	event_id = random_bytes_str(16)
	setattr(threadlocal, 'event_id', event_id)
	setattr(threadlocal, 'event_op', endpoint)
	setattr(threadlocal, 'event_user', None)
	print(f'MSG [{datetime.datetime.now()}] [{endpoint}] {event_id}: path={path}, obj={obj}', file = sys.stderr)
	return event_id

def setEventUser(user) :
	setattr(threadlocal, 'event_user', user)

def getEventID() :
	if hasattr(threadlocal, 'event_id') :
		return getattr(threadlocal, 'event_id')
	return ''

def setEventOp(op) :
	setattr(threadlocal, 'event_op', op)

def setEventID(event_id) :
	setattr(threadlocal, 'event_id', event_id)

def log(op = '', level = "MSG", obj = None) :
	event_id = getEventID()
	event_op = getattr(threadlocal, 'event_op') or op
	event_user = getattr(threadlocal, 'event_user') or {'profile': {'username': '<anonymous>'}}
	print(f"{level} [{event_user['profile']['username']}] [{datetime.datetime.now()}] [{event_op}] {event_id}: {obj}", file = sys.stderr)

def log_e(event_id, user, op = '', level = "MSG", obj = None) :
	print(f"{level} [{user['profile']['username']}] [{datetime.datetime.now()}] [{op}] {event_id}: {obj}", file = sys.stderr)

def log_ne(op = '', level = "MSG", obj = None) :
	print(f"{level} [{datetime.datetime.now()}] [{op}]: {obj}", file = sys.stderr)
