
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, MongoTransaction
from utils.exceptions import UserError

from db import tagdb, client

from bson import ObjectId

import redis_lock
from utils.rwlock import usingResource, modifyingResource
from utils.logger import log
from services.tcb import filterOperation

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
	filterOperation('breakLink', user, vid)
	with redis_lock.Lock(rdb, 'editLink'), MongoTransaction(client) as s :
		nodes = _getAllCopies(vid)
		log(obj = {'old_clique': nodes, 'node_remove': vid})
		if nodes :
			for node in nodes :
				_removeThisCopy(node, vid, makeUserMeta(user), session = s())
			tagdb.update_item_query(ObjectId(vid), {"$set": {"item.copies": []}}, makeUserMeta(user), session = s())
		s.mark_succeed()

@usingResource('tags')
def syncTags(dst, src, user):
	if dst == src :
		raise UserError('SAME_VIDEO')
	filterOperation('syncTags', user, (dst, src))
	src_item, src_tags, _, _ = tagdb.retrive_item_with_tag_category_map(src, 'CHS')
	log(obj = {'src_tags': src_tags, 'src_id': src})
	dst_item = tagdb.retrive_item(dst)
	if dst_item is None :
		raise UserError('ITEM_NOT_EXIST')
	with redis_lock.Lock(rdb, "videoEdit:" + dst_item["item"]["unique_id"]), MongoTransaction(client) as s:
		tagdb.update_item_tags_merge(ObjectId(dst), src_tags, makeUserMeta(user), session = s())
		s.mark_succeed()

@usingResource('tags')
def broadcastTags(src, user):
	filterOperation('broadcastTags', user, src)
	_, src_tags, _, _ = tagdb.retrive_item_with_tag_category_map(src, 'CHS')
	log(obj = {'src_tags': src_tags, 'src_id': src})
	with redis_lock.Lock(rdb, "editLink"), MongoTransaction(client) as s :
		copies = _getAllCopies(src, session = s())
		log(obj = {'clique': copies})
		for copy in copies:
			if copy != ObjectId(src) : # prevent self updating
				copy_obj = tagdb.retrive_item({"_id": ObjectId(copy)}, session = s())
				assert copy_obj is not None, 'copy_obj %s not exist' % copy
				with redis_lock.Lock(rdb, "videoEdit:" + copy_obj["item"]["unique_id"]):
					tagdb.update_item_tags_merge(ObjectId(copy), src_tags, makeUserMeta(user), session = s())
		s.mark_succeed()
