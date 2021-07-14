
from db import db, client
from bson import ObjectId
from datetime import datetime
from utils.dbtools import MongoTransaction
from utils.exceptions import UserError

def createNotification(note_type : str, dst_user : ObjectId, session = None, other = None) :
	"""
	create a Notification
	params:
		note_type: one of 'forum_reply', 'comment_reply', 'system_message', 'dm', 'post_result'
	"""
	obj = {
		"type": note_type,
		"time": datetime.now(),
		"read": False,
		"to": dst_user
	}
	if other :
		for (k, v) in other.items() :
			obj[k] = v
	return db.notes.insert_one(obj, session = session).inserted_id

def createSystemNotification(dst_user : ObjectId, title: str, content: str, session = None, other = None) :
	obj = {
		"type": "system_message",
		"time": datetime.now(),
		"read": False,
		"title": title,
		"content": content,
		"to": dst_user
	}
	if other :
		for (k, v) in other.items() :
			obj[k] = v
	return db.notes.insert_one(obj, session = session).inserted_id

def createDirectMessage(src_user: ObjectId, dst_user: ObjectId, other = None) :
	obj = {
		"type": 'dm',
		"time": datetime.now(),
		"read": False,
		"to": dst_user,
		"src": src_user,
	}
	if other :
		for (k, v) in other.items() :
			obj[k] = v
	with MongoTransaction(client) as s :
		return db.notes.insert_one(obj, session = s()).inserted_id

def getUnreadNotificationCount(user, note_type: str = 'all') :
	if note_type == 'all' :
		return db.notes.find({'to': user['_id'], 'read': False}).count()
	else :
		return db.notes.find({'to': user['_id'], 'read': False, 'type': note_type}).count()

def listMyNotificationUnread(user, note_type: str = 'all') :
	if note_type == 'all' :
		objs = db.notes.find({'to': user['_id'], 'read': False}).sort([("time", -1)])
	else :
		objs = db.notes.find({'to': user['_id'], 'read': False, 'type': note_type}).sort([("time", -1)])
	note_count = objs.count()
	return [i for i in objs], note_count

def listMyNotificationAll(user, offset, limit, note_type: str = 'all') :
	if note_type == 'all' :
		objs = db.notes.find({'to': user['_id']}).sort([("time", -1)]).skip(offset).limit(limit)
	else :
		objs = db.notes.find({'to': user['_id'], 'type': note_type}).sort([("time", -1)]).skip(offset).limit(limit)
	note_count = objs.count()
	return [i for i in objs], note_count

def markRead(user, note_ids) :
	if isinstance(note_ids, str) :
		note_ids = [note_ids]
	assert isinstance(note_ids, list)
	note_ids = [ObjectId(i) for i in note_ids]
	with MongoTransaction(client) as s :
		# TODO: one can mark other's notifications as read here, add filtering later
		db.notes.update_many({'_id': {'$in': note_ids}, 'to': user['_id']}, {'$set': {'read': True}}, session = s())
		s.mark_succeed()

def markAllRead(user, note_type: str = 'all') :
	with MongoTransaction(client) as s :
		if note_type == 'all' :
			db.notes.update_many({'to': user['_id']}, {'$set': {'read': True}}, session = s())
		else :
			db.notes.update_many({'to': user['_id'], 'type': note_type}, {'$set': {'read': True}}, session = s())
		s.mark_succeed()

def broadcastNotification(session = None, other = None) :
	"""
	similar to createNotification but does so for everyone!
	"""
	for u in db.users.find({}) :
		createNotification('system_message', ObjectId(u['_id']), session = session, other = other)

def broadcastNotificationWithContent(content: str) :
	"""
	similar to createNotification but does so for everyone!
	"""
	if len(content) > 65536 :
		raise UserError('CONTENT_TOO_LONG')
	with MongoTransaction(client) as s :
		for u in db.users.find({}) :
			createNotification('system_message', ObjectId(u['_id']), session = s(), other = {'content': content})
