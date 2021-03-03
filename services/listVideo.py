
import pymongo
import sys
import json

from bson import ObjectId
from db import tagdb as db
from .tagStatistics import getPopularTags, getCommonTags, updateTagSearch
from utils.exceptions import UserError
from utils.logger import log
from services.tcb import filterVideoList
from bson.json_util import dumps
from services.config import Config

def _filterPlaceholder(videos) :
	return list(filter(lambda x: not ('placeholder' in x['item'] and x['item']['placeholder']), videos))

def listVideoRandimzied(user, limit, query_str = '', user_language = 'CHS', qtype = 'tag', additional_constraint = '', human_readable_tag = False) :
	query_obj, _ = db.compile_query(query_str, qtype)
	query_obj_extra, _ = db.compile_query(additional_constraint, 'tag')
	log(obj = {'query': dumps(query_obj)})
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
		else :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': user['settings']['blacklist']}}, query_obj_extra]}
	else :
		query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
	videos = list(db.aggregate([
		{'$match': query_obj},
		{'$sample': {'size': limit * 2}}
	]))
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
		if human_readable_tag :
			videos[i]['tags_readable'] = db.translate_tag_ids_to_user_language(videos[i]['tags'], user_language)[0]
	videos = _filterPlaceholder(videos)
	videos = videos[: limit]
	return videos, getCommonTags(user_language, videos)

def listVideoQuery(user, query_str, offset, limit, order = 'latest', user_language = 'CHS', hide_placeholder = True, qtype = 'tag', additional_constraint = '', human_readable_tag = False):
	log(obj = {'q': query_str, 'offset': offset, 'limit': limit, 'order': order, 'lang': user_language})
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	query_obj, tags = db.compile_query(query_str, qtype)
	query_obj_extra, _ = db.compile_query(additional_constraint, 'tag')
	log(obj = {'query': dumps(query_obj)})
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
		else :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': user['settings']['blacklist']}}, query_obj_extra]}
	else :
		query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
	updateTagSearch(tags)
	exStats1 = None
	exStats2 = None
	try :
		result = db.retrive_items(query_obj)
		exStats1 = result.explain()
		if order == 'latest':
			result = result.sort([("meta.created_at", -1)])
		elif order == 'oldest':
			result = result.sort([("meta.created_at", 1)])
		elif order == 'video_latest':
			result = result.sort([("item.upload_time", -1)])
		elif order == 'video_oldest':
			result = result.sort([("item.upload_time", 1)])
		elif order == 'last_modified':
			result = result.sort([("meta.modified_at", -1)])
		ret = result.skip(offset).limit(limit)
		exStats2 = ret.explain()
		count = ret.count()
		videos = [item for item in ret]
		videos = filterVideoList(videos, user)
		for i in range(len(videos)) :
			videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
			if human_readable_tag :
				videos[i]['tags_readable'] = db.translate_tag_ids_to_user_language(videos[i]['tags'], user_language)[0]
		if hide_placeholder :
			videos = _filterPlaceholder(videos)
	except pymongo.errors.OperationFailure as ex:
		if '$not' in str(ex) :
			raise UserError('FAILED_NOT_OP')
		else :
			log(level = 'ERR', obj = {'ex': str(ex)})
			raise UserError('FAILED_UNKNOWN')
	return videos, getCommonTags(user_language, videos), count, query_obj, exStats1, exStats2

def listVideo(offset, limit, user, order = 'latest', user_language = 'CHS', hide_placeholder = True, additional_constraint = '', human_readable_tag = False):
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	query_obj_extra, _ = db.compile_query(additional_constraint, 'tag')
	query_obj = {}
	empty_query = True
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			empty_query = False
			query_obj = {'$and': [{'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
		else :
			if user['settings']['blacklist'] or query_obj_extra :
				empty_query = False
			query_obj = {'$and': [{'tags': {'$nin': user['settings']['blacklist']}}, query_obj_extra]}
	else :
		empty_query = False
		query_obj = {'$and': [{'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
	if empty_query :
		query_obj = {}
	exStats1 = None
	exStats2 = None
	result = db.retrive_items(query_obj)
	exStats1 = result.explain()
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	elif order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	elif order == 'video_latest':
		result = result.sort([("item.upload_time", -1)])
	elif order == 'video_oldest':
		result = result.sort([("item.upload_time", 1)])
	elif order == 'last_modified':
		result = result.sort([("meta.modified_at", -1)])
	videos = result.skip(offset).limit(limit)
	exStats2 = videos.explain()
	video_count = videos.count()
	videos = [i for i in videos]
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
		if human_readable_tag :
			videos[i]['tags_readable'] = db.translate_tag_ids_to_user_language(videos[i]['tags'], user_language)[0]
	if hide_placeholder :
		videos = _filterPlaceholder(videos)
	tags, pops = getPopularTags(user_language)
	return videos, video_count, tags, pops, query_obj, exStats1, exStats2

def listMyVideo(offset, limit, user, order = 'latest', human_readable_tag = False, user_language = 'CHS'):
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	result = db.retrive_items({'meta.created_by': ObjectId(user['_id'])})
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	elif order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	elif order == 'video_latest':
		result = result.sort([("item.upload_time", -1)])
	elif order == 'video_oldest':
		result = result.sort([("item.upload_time", 1)])
	elif order == 'last_modified':
		result = result.sort([("meta.modified_at", -1)])
	videos = result.skip(offset).limit(limit)
	video_count = videos.count()
	videos = [i for i in videos]
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
		if human_readable_tag :
			videos[i]['tags_readable'] = db.translate_tag_ids_to_user_language(videos[i]['tags'], user_language)[0]
	return videos, video_count

def listYourVideo(uid, offset, limit, user, order = 'latest', human_readable_tag = False, user_language = 'CHS'):
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	result = db.retrive_items({'meta.created_by': ObjectId(uid)})
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	elif order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	elif order == 'video_latest':
		result = result.sort([("item.upload_time", -1)])
	elif order == 'video_oldest':
		result = result.sort([("item.upload_time", 1)])
	elif order == 'last_modified':
		result = result.sort([("meta.modified_at", -1)])
	videos = result.skip(offset).limit(limit)
	video_count = videos.count()
	videos = [i for i in videos]
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
		if human_readable_tag :
			videos[i]['tags_readable'] = db.translate_tag_ids_to_user_language(videos[i]['tags'], user_language)[0]
	return videos, video_count
