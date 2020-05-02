
from bson import ObjectId
from services.comment import createThread, addComment, addReply, listThread
from utils.exceptions import UserError
from config import Forums, Comments
from utils.dbtools import makeUserMetaObject, makeUserMeta
from services.tcb import filterOperation

from utils.dbtools import MongoTransaction
from db import db, tagdb, client

import bleach

def createForum(name : str, lang : str) : # this can only be used by admin from command line
	tagdb._check_language(lang)
	fid = str(db.forum_metas.insert_one({
		'names' : {
			lang: name
		}
	}).inserted_id)
	return fid

def postThreadToForum(user, forum_id : ObjectId, title : str, text: str, use_bleach = True) : # create a thread and post a comment
	filterOperation('postThreadToForum', user)
	if db.forum_metas.find_one({'_id': forum_id}) is None :
		raise UserError('FORUM_NOT_EXIST')
	if len(title) > Forums.MAX_TITLE_LENGTH :
		raise UserError('TITLE_TOO_LONG')
	l = len(text)
	if l > Comments.MAX_COMMENT_LENGTH_LONG :
		raise UserError('COMMENT_TOO_LONG')
	elif l > Comments.MAX_COMMENT_LENGTH_REGULAR and not filterOperation('postLongComment', user, raise_exception = False) :
		raise UserError('COMMENT_TOO_LONG')
	if use_bleach :
		text = bleach.clean(text, tags = [], attributes = [], styles = [])

	with MongoTransaction(client) as s :
		thread_id = createThread('forum', None, user['_id'], session = s())
		ftid = ObjectId(db.forum_threads.insert_one({
			'forum_id': forum_id,
			'title': title,
			'tid': thread_id,
			'hidden': False,
			'deleted': False,
			'pinned': False,
			'meta': makeUserMetaObject(user)
		}, session = s()).inserted_id)
		db.comment_items.insert_one({
			'thread': thread_id,
			'content': text,
			'hidden': False,
			'deleted': False,
			'upvotes': 0,
			'downvotes': 0,
			'meta': makeUserMetaObject(user)
		}, session = s())
		db.comment_threads.update_one({'_id': thread_id}, {'$inc': {'count': int(1)}, '$set': {'obj_id': ftid}}, session = s())
		s.mark_succeed()
		return str(ftid)

def listForumThreads(forum_id : ObjectId, page_idx : int = 0, page_size : int = 30, order = 'last_modified') :
	if db.forum_metas.find_one({'_id': forum_id}) is None :
		raise UserError('FORUM_NOT_EXIST')
	if order not in ['last_modified'] :
		raise UserError('INCORRECT_ORDER')
	if order == 'last_modified' :
		sort_obj = {"meta.modified_at": -1}
	all_items = db.forum_threads.aggregate([
		{'$match': {'forum_id': forum_id, 'deleted': False, 'pinned': False}},
		{'$sort': sort_obj},
		{'$skip': page_idx * page_size},
		{'$limit': page_size},
		{'$lookup': {'from': 'comment_threads', 'localField': 'tid', 'foreignField': '_id', 'as': 'thread_obj'}}
	])
	all_pinned_items = db.forum_threads.aggregate([
		{'$match': {'forum_id': forum_id, 'deleted': False, 'pinned': True}},
		{'$sort': sort_obj},
		{'$lookup': {'from': 'comment_threads', 'localField': 'tid', 'foreignField': '_id', 'as': 'thread_obj'}}
	])
	all_items_list = list(all_pinned_items) + list(all_items)
	return all_items_list[: page_size]

def viewSingleForumThread(ftid : ObjectId) :
	ft_obj = db.forum_threads.find_one({'_id': ftid})
	if ft_obj is None :
		raise UserError('THREAD_NOT_EXIST')
	if ft_obj['deleted'] :
		raise UserError('THREAD_NOT_EXIST') # deleted counts as non-exist
	title = ft_obj['title']
	replys, users = listThread(ft_obj['tid'])
	return replys, users, title

def addToThread(user, ftid : ObjectId, content : str) :
	ft_obj = db.forum_threads.find_one({'_id': ftid})
	if ft_obj is None :
		raise UserError('THREAD_NOT_EXIST')
	if ft_obj['deleted'] :
		raise UserError('THREAD_NOT_EXIST') # deleted counts as non-exist
	return addComment(user, ft_obj['tid'], content, notification_type = 'forum_reply')

def addReplyToThread(user, reply_to : ObjectId, text : str) :
	return addReply(user, reply_to, text, notification_type = 'forum_reply')

def deleteThread(user, ftid : ObjectId) :
	ft_obj = db.forum_threads.find_one({'_id': ftid})
	if ft_obj is None :
		raise UserError('THREAD_NOT_EXIST')
	if ft_obj['deleted'] :
		raise UserError('THREAD_NOT_EXIST') # deleted counts as non-exist
	filterOperation('commentAdmin', user, ft_obj)
	db.forum_threads.update_one({'_id': ftid}, {'$set': {'deleted': True}})

def pinThread(user, ftid : ObjectId, pinned : bool) :
	ft_obj = db.forum_threads.find_one({'_id': ftid})
	if ft_obj is None :
		raise UserError('THREAD_NOT_EXIST')
	if ft_obj['deleted'] :
		raise UserError('THREAD_NOT_EXIST') # deleted counts as non-exist
	filterOperation('commentAdmin', user)
	db.forum_threads.update_one({'_id': ftid}, {'$set': {'pinned': pinned}})

