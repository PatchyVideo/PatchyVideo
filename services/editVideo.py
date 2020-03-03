
from db import tagdb, client
from utils.dbtools import makeUserMeta, MongoTransaction
from utils.rwlock import usingResource, modifyingResource
from utils.exceptions import UserError
from utils.tagtools import translateTagsToPreferredLanguage
from services.postVideo import postTask
from services.tcb import filterSingleVideo, filterOperation

import pymongo
from init import rdb
from bson import ObjectId
import redis_lock
from config import VideoConfig, TagsConfig
from bson.json_util import dumps, loads
from utils.logger import log, getEventID

@usingResource('tags')
def editVideoTags(vid, tags, user):
	log(obj = {'tags': tags, 'vid': vid})
	filterOperation('editVideoTags', user, vid)
	filterSingleVideo(vid, user)
	if len(tags) > VideoConfig.MAX_TAGS_PER_VIDEO :
		raise UserError('TAGS_LIMIT_EXCEEDED')
	tagdb.verify_tags(tags)
	item = tagdb.db.items.find_one({'_id': ObjectId(vid)})
	if item is None:
		raise UserError('ITEM_NOT_EXIST')
	if len(tags) > VideoConfig.MAX_TAGS_PER_VIDEO:
		raise UserError('TOO_MANY_TAGS')
	with redis_lock.Lock(rdb, "videoEdit:" + item['item']['unique_id']), MongoTransaction(client) as s :
		tagdb.update_item_tags(item, tags, makeUserMeta(user), session = s())
		s.mark_succeed()

def getVideoTags(vid, user_language, user) :
	filterSingleVideo(vid, user)
	item, tags, category_tag_map, tag_category_map = tagdb.retrive_item_with_tag_category_map(vid, user_language)
	return tags

def refreshVideoDetail(vid, user) :
	log(obj = {'vid': vid})
	filterOperation('refreshVideoDetail', user, vid)
	filterSingleVideo(vid, user)
	item = tagdb.retrive_item(vid)
	if item is None :
		raise UserError('ITEM_NOT_EXIST')
	json_str = dumps({
		'url' : item['item']['url'],
		'tags' : [],
		'dst_copy' : '',
		'dst_playlist' : '',
		'dst_rank' : -1,
		'other_copies' : [],
		'user' : user,
		'repost_type': 'repost',
		'playlist_ordered' : None,
		'update_video_detail': True,
		'event_id': getEventID()
	})
	postTask(json_str)

def refreshVideoDetailURL(url, user) :
	log(obj = {'url': url})
	filterOperation('refreshVideoDetailURL', user, url)
	json_str = dumps({
		'url' : url,
		'tags' : [],
		'dst_copy' : '',
		'dst_playlist' : '',
		'dst_rank' : -1,
		'other_copies' : [],
		'user' : user,
		'playlist_ordered' : None,
		'update_video_detail': True,
		'event_id': getEventID()
	})
	postTask(json_str)

def setVideoRepostType(vid, repost_type, user) :
	filterOperation('setVideoRepostType', user)
	if repost_type not in ['official', 'official_repost', 'authorized_translation', 'authorized_repost', 'translation', 'repost'] :
		raise UserError('INCORRECT_REPOST_TYPE')
	video_obj = tagdb.retrive_item(vid)
	if video_obj is None :
		raise UserError('VIDEO_NOT_FOUND')
	lock_id = "videoEdit:" + video_obj['item']['unique_id']
	with redis_lock.Lock(rdb, lock_id), MongoTransaction(client) as s :
		tagdb.update_item_query(video_obj, {'$set': {'item.repost_type': repost_type}}, session = s())
		s.mark_succeed()

def _batchedRead(cursor, batch_size = 100) :
	batch = []
	try :
		for _ in range(batch_size) :
			batch.append(next(cursor))
	except StopIteration :
		pass
	return batch

def editVideoTagsQuery(query, query_type, tags_to_add, tags_to_remove, user) :
	if query_type not in ['tag', 'text'] :
		raise UserError('INCORRECT_QUERY_TYPE')
	filterOperation('batchVideoTagEdit', user)
	query_obj, _ = tagdb.compile_query(query)
	log(obj = {'query': dumps(query_obj)})
	tagids_to_add = tagdb.filter_and_translate_tags(tags_to_add)
	tagids_to_remove = tagdb.filter_and_translate_tags(tags_to_remove)
	try :
		count = 0
		with MongoTransaction(client) as s_read, MongoTransaction(client) as s_write :
			result_cursor = tagdb.retrive_items(query_obj, session = s_read())
			batch = _batchedRead(result_cursor)
			while batch :
				item_ids = [item['_id'] for item in batch]
				tagdb.update_many_items_tags_pull(item_ids, tagids_to_remove, makeUserMeta(user), session = s_write())
				tagdb.update_many_items_tags_merge(item_ids, tagids_to_add, makeUserMeta(user), session = s_write())
				count += len(batch)
				batch = _batchedRead(result_cursor)
			s_write.mark_succeed()
		return count
	except pymongo.errors.OperationFailure as ex:
		if '$not' in str(ex) :
			raise UserError('FAILED_NOT_OP')
		else :
			log(level = 'ERR', obj = {'ex': str(ex)})
			raise UserError('FAILED_UNKNOWN')
