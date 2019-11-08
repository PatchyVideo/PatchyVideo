
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, MongoTransaction

from spiders import dispatch
from db import tagdb, client

from bson import ObjectId

import redis_lock

def getAllCopies(vid) :
	if not vid :
		return []
	this_video = tagdb.retrive_item({"_id": ObjectId(vid)})
	if this_video is None :
		return []
	copies = this_video['item']['copies']
	# add self
	copies.append(ObjectId(vid))
	# use set to remove duplicated items
	return list(set(copies))

def removeThisCopy(dst_vid, this_vid, session):
	if this_vid is None :
		return
	dst_video = tagdb.retrive_item({"_id": ObjectId(dst_vid)}, session)
	if dst_video is None :
		return
	dst_copies = dst_video['item']['copies']
	dst_copies = list(set(dst_copies) - set([ObjectId(this_vid)]))
	tagdb.update_item_query(ObjectId(dst_vid), {"$set": {"item.copies": dst_copies}}, session)

def breakLink(vid, user):
	with redis_lock.Lock(rdb, 'editLink'), MongoTransaction(client) as s :
		nodes = getAllCopies(vid)
		if nodes :
			for node in nodes :
				removeThisCopy(node, vid, s())
			tagdb.update_item_query(ObjectId(vid), {"$set": {"item.copies": []}}, s())
			s.mark_succeed()

def syncTags(dst, src, user):
	src_item = tagdb.retrive_item({"_id": ObjectId(src)})
	if src_item is None:
		return "ITEM_NOT_EXIST"
	src_tags = src_item['tags']
	with redis_lock.Lock(rdb, "videoEdit:" + src_item["item"]["unique_id"]), MongoTransaction(client) as s:
		ret = tagdb.update_item_tags_merge(ObjectId(dst), src_tags, user, s())
		if ret == 'SUCCEED':
			s.mark_succeed()
		return ret
