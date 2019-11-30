
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, MongoTransaction
from utils.exceptions import UserError

from spiders import dispatch
from db import tagdb, client

from bson import ObjectId

import redis_lock
from utils.rwlock import usingResource, modifyingResource

def _getAllCopies(vid_or_obj, session = None) :
	if not vid_or_obj :
		return []
	this_video = None
	if isinstance(vid_or_obj, str) or isinstance(vid_or_obj, ObjectId) :
		this_video = tagdb.retrive_item({"_id": ObjectId(vid_or_obj)}, session = session)
	else :
		this_video = vid_or_obj
	if this_video is None :
		return []
	copies = this_video['item']['copies']
	# add self
	copies.append(this_video['_id'])
	# use set to remove duplicated items
	return list(set(copies))

def _removeThisCopy(dst_vid, this_vid, user, session):
	if this_vid is None :
		return
	dst_video = tagdb.retrive_item({"_id": ObjectId(dst_vid)}, session)
	if dst_video is None :
		return
	dst_copies = dst_video['item']['copies']
	dst_copies = list(set(dst_copies) - set([ObjectId(this_vid)]))
	tagdb.update_item_query(ObjectId(dst_vid), {"$set": {"item.copies": dst_copies}}, user, session)

def breakLink(vid, user):
	with redis_lock.Lock(rdb, 'editLink'), MongoTransaction(client) as s :
		nodes = _getAllCopies(vid)
		if nodes :
			for node in nodes :
				_removeThisCopy(node, vid, makeUserMeta(user), s())
			tagdb.update_item_query(ObjectId(vid), {"$set": {"item.copies": []}}, makeUserMeta(user), s())
			s.mark_succeed()

@usingResource('tags')
def syncTags(dst, src, user):
	src_item = tagdb.retrive_item({"_id": ObjectId(src)})
	if src_item is None:
		raise UserError("ITEM_NOT_EXIST")
	src_tags = src_item['tags']
	with redis_lock.Lock(rdb, "videoEdit:" + src_item["item"]["unique_id"]), MongoTransaction(client) as s:
		ret = tagdb.update_item_tags_merge(ObjectId(dst), src_tags, makeUserMeta(user), s())
		if ret == 'SUCCEED':
			s.mark_succeed()
		return ret

@usingResource('tags')
def broadcastTags(src, user):
	src_item = tagdb.retrive_item({"_id": ObjectId(src)})
	if src_item is None:
		raise UserError("ITEM_NOT_EXIST")
	src_tags = src_item['tags']
	with redis_lock.Lock(rdb, "editLink"), MongoTransaction(client) as s :
		copies = _getAllCopies(src, session = s())
		for copy in copies:
			if copy != ObjectId(src) : # prevent self updating
				copy_obj = tagdb.retrive_item({"_id": ObjectId(copy)}, session = s())
				if copy_obj is None:
					raise UserError("ITEM_NOT_EXIST")
				with redis_lock.Lock(rdb, "videoEdit:" + copy_obj["item"]["unique_id"]):
					ret = tagdb.update_item_tags_merge(ObjectId(copy), src_tags, makeUserMeta(user), s())
					if ret != 'SUCCEED':
						raise UserError("ITEM_NOT_EXIST")
		s.mark_succeed()
		return ret
