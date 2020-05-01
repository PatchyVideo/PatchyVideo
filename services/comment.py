
import redis_lock
import bleach

from bson import ObjectId

from init import rdb
from db import db, client
from utils.dbtools import MongoTransaction
from utils.exceptions import UserError
from utils.dbtools import makeUserMetaObject, makeUserMeta
from services.tcb import filterOperation
from config import Comments
from services.notifications import createNotification
from utils.logger import log
from datetime import datetime

"""
Standalone comment APIs
"""

"""
Comments are grouped in to threads, each object(video/user/playlist) can only have up to one thread associated with it
a comment contains:
comment: {
	"thread": thread id
	"content": comment content,
	"meta" : {
		...
	},
	"hidden": not shown by default,
	"deleted": you cannot see this,
	"upvotes",
	"downvotes"
}
a sub comment contains:
sub_comment: {
	"parent": parent comment id,
	"reply_to": reply to comment id,
	"content": comment content,
	"meta" : {
		...
	}
	"hidden": not shown by default,
	"deleted": you cannot see this,
	"upvotes",
	"downvotes"
}
"""

def createThread(obj_type: str, obj_id : ObjectId, owner : ObjectId, session = None) : # thread is created by the website automatically, not user
	# owner is an user id, who will receive notification if new comment was added
	# obj is video/playlist/user
	tid = db.comment_threads.insert_one({'count': 0, 'owner': owner, 'obj_type': obj_type, 'obj_id': obj_id}, session = session).inserted_id
	return ObjectId(tid)

def addComment(user, thread_id : ObjectId, text : str, notification_type : str = 'comment_reply') : # user can add comments
	filterOperation('postComment', user)
	text = bleach.clean(text, tags = [], attributes = [], styles = [])
	l = len(text)
	if l > Comments.MAX_COMMENT_LENGTH_LONG :
		raise UserError('COMMENT_TOO_LONG')
	elif l > Comments.MAX_COMMENT_LENGTH_REGULAR and not filterOperation('postLongComment', user, raise_exception = False) :
		raise UserError('COMMENT_TOO_LONG')
	thread_obj = db.comment_threads.find_one({'_id': thread_id})
	if thread_obj is None :
		raise UserError('THREAD_NOT_EXIST')
	with redis_lock.Lock(rdb, "thread:" + str(thread_id)), MongoTransaction(client) as s :
		cid = str(db.comment_items.insert_one({
			'thread': thread_id,
			'content': text,
			'hidden': False,
			'deleted': False,
			'pinned': False,
			'upvotes': 0,
			'downvotes': 0,
			'meta': makeUserMetaObject(user)
		}, session = s()).inserted_id)
		db.comment_threads.update_one({'_id': thread_id}, {'$inc': {'count': int(1)}}, session = s())
		note_obj = {
			"cid": ObjectId(cid),
			"replied_by": makeUserMeta(user),
			"content": text[:Comments.NOTIFICATION_CONTENT_LENGTH]
		}
		# ===========================================================
		if 'obj_type' in thread_obj and 'obj_id' in thread_obj :
			note_obj['replied_type'] = thread_obj['obj_type']
			note_obj['replied_obj'] = thread_obj['obj_id']
		else :
			obj = db.videos.find_one({'comment_thread': thread_id}, session = s())
			if obj :
				note_obj['replied_type'] = 'video'
				note_obj['replied_obj'] = obj['_id']
				db.comment_threads.update_one({'_id': thread_id}, {'$set': {'obj_type': 'video', 'obj_id': obj['_id']}}, session = s())
			else :
				obj = db.playlists.find_one({'comment_thread': thread_id}, session = s())
				if obj :
					note_obj['replied_type'] = 'playlist'
					note_obj['replied_obj'] = obj['_id']
					db.comment_threads.update_one({'_id': thread_id}, {'$set': {'obj_type': 'playlist', 'obj_id': obj['_id']}}, session = s())
				else :
					obj = db.users.find_one({'comment_thread': thread_id}, session = s())
					if obj :
						note_obj['replied_type'] = 'user'
						note_obj['replied_obj'] = obj['_id']
						db.comment_threads.update_one({'_id': thread_id}, {'$set': {'obj_type': 'user', 'obj_id': obj['_id']}}, session = s())
					else :
						log(level = 'ERR', obj = {'msg': 'orphan thread found!!', 'thread_id': thread_id, 'thread_obj': thread_obj})
						raise UserError('UNKNOWN_ERROR')
		# ===========================================================
		if notification_type : # empty means do not notify user
			createNotification(notification_type, thread_obj['owner'], session = s(), other = note_obj)
		if note_obj['replied_type'] == 'forum' : # forum comment, set modified_at date
			db.forum_threads.update_one({'_id': note_obj['replied_obj']}, {'$set': {'meta.modified_at': datetime.now(), 'meta.modified_by': user['_id']}}, session = s())
		s.mark_succeed()
		return cid

def addReply(user, reply_to : ObjectId, text : str, notification_type : str = 'comment_reply') : # user can add comments
	"""
	reply_to: comment id
	"""
	filterOperation('postComment', user)
	text = bleach.clean(text, tags = [], attributes = [], styles = [])
	l = len(text)
	if l > Comments.MAX_COMMENT_LENGTH_LONG :
		raise UserError('COMMENT_TOO_LONG')
	elif l > Comments.MAX_COMMENT_LENGTH_REGULAR and not filterOperation('postLongComment', user, raise_exception = False) :
		raise UserError('COMMENT_TOO_LONG')
	parent_obj = db.comment_items.find_one({'_id': reply_to})
	if parent_obj is None :
		raise UserError('PARENT_NOT_EXIST')
	with MongoTransaction(client) as s :
		if 'thread' in parent_obj : # reply to primary comment
			cid = str(db.comment_items.insert_one({
				'parent': reply_to,
				'content': text,
				'hidden': False,
				'deleted': False,
				'pinned': False,
				'upvotes': 0,
				'downvotes': 0,
				'meta': makeUserMetaObject(user)
			}, session = s()).inserted_id)
			thread_obj = db.comment_threads.find_one({'_id': parent_obj['thread']}, session = s())
			if thread_obj is None :
				log(level = 'ERR', obj = {'msg': 'orphan comment found!!', 'cid': parent_obj['_id'], 'obj': parent_obj})
				raise UserError('UNKNOWN_ERROR')
			thread_id = thread_obj['_id']
		else : # reply to secondary comment
			cid = str(db.comment_items.insert_one({
				'parent': parent_obj['parent'],
				'reply_to': reply_to,
				'content': text,
				'hidden': False,
				'deleted': False,
				'pinned': False,
				'upvotes': 0,
				'downvotes': 0,
				'meta': makeUserMetaObject(user)
			}, session = s()).inserted_id)
			parent_parent_obj = db.comment_items.find_one({'_id': parent_obj['parent']}, session = s())
			if parent_parent_obj is None :
				log(level = 'ERR', obj = {'msg': 'orphan comment found!!', 'cid': parent_obj['_id'], 'obj': parent_obj})
				raise UserError('UNKNOWN_ERROR')
			thread_obj = db.comment_threads.find_one({'_id': parent_parent_obj['thread']}, session = s())
			if thread_obj is None :
				log(level = 'ERR', obj = {'msg': 'orphan comment found!!', 'cid': parent_parent_obj['_id'], 'obj': parent_parent_obj})
				raise UserError('UNKNOWN_ERROR')
			thread_id = thread_obj['_id']
		note_obj = {
			"cid": ObjectId(cid),
			"replied_by": makeUserMeta(user),
			"content": text[:Comments.NOTIFICATION_CONTENT_LENGTH]
		}
		# ===========================================================
		if 'obj_type' in thread_obj and 'obj_id' in thread_obj :
			note_obj['replied_type'] = thread_obj['obj_type']
			note_obj['replied_obj'] = thread_obj['obj_id']
		else :
			obj = db.videos.find_one({'comment_thread': thread_id}, session = s())
			if obj :
				note_obj['replied_type'] = 'video'
				note_obj['replied_obj'] = obj['_id']
				db.comment_threads.update_one({'_id': thread_id}, {'$set': {'obj_type': 'video', 'obj_id': obj['_id']}}, session = s())
			else :
				obj = db.playlists.find_one({'comment_thread': thread_id}, session = s())
				if obj :
					note_obj['replied_type'] = 'playlist'
					note_obj['replied_obj'] = obj['_id']
					db.comment_threads.update_one({'_id': thread_id}, {'$set': {'obj_type': 'playlist', 'obj_id': obj['_id']}}, session = s())
				else :
					obj = db.users.find_one({'comment_thread': thread_id}, session = s())
					if obj :
						note_obj['replied_type'] = 'user'
						note_obj['replied_obj'] = obj['_id']
						db.comment_threads.update_one({'_id': thread_id}, {'$set': {'obj_type': 'user', 'obj_id': obj['_id']}}, session = s())
					else :
						log(level = 'ERR', obj = {'msg': 'orphan thread found!!', 'thread_id': thread_id, 'thread_obj': thread_obj})
						raise UserError('UNKNOWN_ERROR')
		# ===========================================================
		if notification_type : # empty means do not notify user
			createNotification(notification_type, parent_obj['meta']['created_by'], session = s(), other = note_obj)
		if note_obj['replied_type'] == 'forum' : # forum reply, set modified_at date
			db.forum_threads.update_one({'_id': note_obj['replied_obj']}, {'$set': {'meta.modified_at': datetime.now(), 'meta.modified_by': user['_id']}}, session = s())
		s.mark_succeed()

def hideComment(user, comment_id : ObjectId) :
	comm_obj = db.comment_items.find_one({'_id': comment_id})
	if comm_obj is None :
		raise UserError('COMMENT_NOT_EXIST')
	filterOperation('commentAdmin', user, comm_obj)
	db.comment_items.update_one({'_id': comment_id}, {'$set': {'hidden': True}})

def delComment(user, comment_id : ObjectId) :
	comm_obj = db.comment_items.find_one({'_id': comment_id})
	if comm_obj is None :
		raise UserError('COMMENT_NOT_EXIST')
	filterOperation('commentAdmin', user, comm_obj)
	db.comment_items.update_one({'_id': comment_id}, {'$set': {'deleted': True}})

def editComment(user, text : str, comment_id : ObjectId) :
	comm_obj = db.comment_items.find_one({'_id': comment_id})
	if comm_obj is None :
		raise UserError('COMMENT_NOT_EXIST')
	text = bleach.clean(text, tags = [], attributes = [], styles = [])
	l = len(text)
	if l > Comments.MAX_COMMENT_LENGTH_LONG :
		raise UserError('COMMENT_TOO_LONG')
	elif l > Comments.MAX_COMMENT_LENGTH_REGULAR and not filterOperation('postLongComment', user, raise_exception = False) :
		raise UserError('COMMENT_TOO_LONG')
	filterOperation('commentAdmin', user, comm_obj)
	with MongoTransaction(client) as s :
		db.comment_items.update_one({'_id': comment_id}, {'$set': {'content': text, 'edited': True}}, session = s())
		db.comment_items.update_one({'_id': comment_id}, {'$set': {'meta.modified_by': datetime.now()}}, session = s())
		s.mark_succeed()

def pinComment(user, comment_id : ObjectId, pinned : bool) :
	comm_obj = db.comment_items.find_one({'_id': comment_id})
	if comm_obj is None :
		raise UserError('COMMENT_NOT_EXIST')
	parent_obj = db.comment_items.find_one({'_id': comm_obj['parent']})
	if parent_obj is None :
		raise UserError('PARENT_NOT_EXIST')
	filterOperation('commentAdmin', user, parent_obj)
	db.comment_items.update_one({'_id': comment_id}, {'$set': {'pinned': pinned}})

def listThread(thread_id : ObjectId) :
	if db.comment_threads.find_one({'_id': thread_id}) is None :
		raise UserError('THREAD_NOT_EXIST')
	ret = list(db.comment_items.aggregate([
		{'$match': {'thread': thread_id, 'pinned': False}},
		{'$lookup': {'from': 'comment_items', 'localField': '_id', 'foreignField': 'parent', 'as': 'children'}}
	]))
	ret_pinned = list(db.comment_items.aggregate([
		{'$match': {'thread': thread_id, 'pinned': True}},
		{'$lookup': {'from': 'comment_items', 'localField': '_id', 'foreignField': 'parent', 'as': 'children'}}
	]))
	all_items = list(ret_pinned) + list(ret)
	users = []
	for comment in all_items :
		users.append(comment['meta']['created_by'])
		if comment['deleted'] :
			comment['content'] = ''
		for child in comment['children'] :
			users.append(child['meta']['created_by'])
			if child['deleted'] :
				child['content'] = ''
	users = db.users.aggregate([
		{'$match': {'_id': {'$in': users}}},
		{'$project': {'profile.username': 1, 'profile.desc': 1, 'profile.image': 1}}
	])
	return all_items, list(users)

def addToVideo(user, vid : ObjectId, text : str) :
	filterOperation('postComment', user)
	video_obj = db.videos.find_one({'_id': vid})
	if video_obj is None :
		raise UserError('VIDEO_NOT_EXIST')
	with redis_lock.Lock(rdb, "videoEdit:" + video_obj["item"]["unique_id"]) :
		if 'comment_thread' in video_obj :
			cid = addComment(user, video_obj['comment_thread'], text)
			return video_obj['comment_thread'], cid
		else :
			with MongoTransaction(client) as s :
				tid = createThread('video', video_obj['_id'], video_obj['meta']['created_by'], session = s())
				db.videos.update_one({'_id': vid}, {'$set': {'comment_thread': tid}})
				s.mark_succeed()
			cid = addComment(user, tid, text)
			return tid, cid
	
def addToPlaylist(user, pid : ObjectId, text : str) :
	filterOperation('postComment', user)
	playlist_obj = db.playlists.find_one({'_id': pid})
	if playlist_obj is None :
		raise UserError('PLAYLIST_NOT_EXIST')
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)) :
		if 'comment_thread' in playlist_obj :
			cid = addComment(user, playlist_obj['comment_thread'], text)
			return playlist_obj['comment_thread'], cid
		else :
			with MongoTransaction(client) as s :
				tid = createThread('playlist', playlist_obj['_id'], playlist_obj['meta']['created_by'], session = s())
				db.playlists.update_one({'_id': pid}, {'$set': {'comment_thread': tid}})
				s.mark_succeed()
			cid = addComment(user, tid, text)
			return tid, cid

def addToUser(user, uid : ObjectId, text : str) :
	filterOperation('postComment', user)
	user_obj = db.users.find_one({'_id': uid})
	if user_obj is None :
		raise UserError('USER_NOT_EXIST')
	with redis_lock.Lock(rdb, "userEdit:" + str(uid)) :
		if 'comment_thread' in user_obj :
			cid = addComment(user, user_obj['comment_thread'], text)
			return user_obj['comment_thread'], cid
		else :
			with MongoTransaction(client) as s :
				tid = createThread('user', uid, uid, session = s())
				db.users.update_one({'_id': uid}, {'$set': {'comment_thread': tid}})
				s.mark_succeed()
			cid = addComment(user, tid, text)
			return tid, cid
