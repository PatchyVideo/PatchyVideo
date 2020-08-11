
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

def listVideoRandimzied(user, page_size, query_str = '', user_language = 'CHS', qtype = 'tag', additional_constraint = '') :
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
		{'$sample': {'size': page_size * 2}}
	]))
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
	videos = _filterPlaceholder(videos)
	videos = videos[: page_size]
	return videos, getCommonTags(user_language, videos)

def listVideoQuery(user, query_str, page_idx, page_size, order = 'latest', user_language = 'CHS', hide_placeholder = True, qtype = 'tag', additional_constraint = ''):
	log(obj = {'q': query_str, 'page': page_idx, 'page_size': page_size, 'order': order, 'lang': user_language})
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
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
		if order == 'oldest':
			result = result.sort([("meta.created_at", 1)])
		if order == 'video_latest':
			result = result.sort([("item.upload_time", -1)])
		if order == 'video_oldest':
			result = result.sort([("item.upload_time", 1)])
		ret = result.skip(page_idx * page_size).limit(page_size)
		exStats2 = ret.explain()
		count = ret.count()
		videos = [item for item in ret]
		videos = filterVideoList(videos, user)
		for i in range(len(videos)) :
			videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
		if hide_placeholder :
			videos = _filterPlaceholder(videos)
	except pymongo.errors.OperationFailure as ex:
		if '$not' in str(ex) :
			raise UserError('FAILED_NOT_OP')
		else :
			log(level = 'ERR', obj = {'ex': str(ex)})
			raise UserError('FAILED_UNKNOWN')
	return videos, getCommonTags(user_language, videos), count, query_obj, exStats1, exStats2

def listVideo(page_idx, page_size, user, order = 'latest', user_language = 'CHS', hide_placeholder = True, additional_constraint = ''):
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
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
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	if order == 'video_latest':
		result = result.sort([("item.upload_time", -1)])
	if order == 'video_oldest':
		result = result.sort([("item.upload_time", 1)])
	videos = result.skip(page_idx * page_size).limit(page_size)
	exStats2 = videos.explain()
	video_count = videos.count()
	videos = [i for i in videos]
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
	if hide_placeholder :
		videos = _filterPlaceholder(videos)
	tags, pops = getPopularTags(user_language)
	return videos, video_count, tags, pops, query_obj, exStats1, exStats2

def listMyVideo(page_idx, page_size, user, order = 'latest'):
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise UserError('INCORRECT_ORDER')
	result = db.retrive_items({'meta.created_by': ObjectId(user['_id'])})
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	if order == 'video_latest':
		result = result.sort([("item.upload_time", -1)])
	if order == 'video_oldest':
		result = result.sort([("item.upload_time", 1)])
	videos = result.skip(page_idx * page_size).limit(page_size)
	video_count = videos.count()
	videos = [i for i in videos]
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
	return videos, video_count

def listYourVideo(uid, page_idx, page_size, user, order = 'latest'):
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise UserError('INCORRECT_ORDER')
	result = db.retrive_items({'meta.created_by': ObjectId(uid)})
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	if order == 'video_latest':
		result = result.sort([("item.upload_time", -1)])
	if order == 'video_oldest':
		result = result.sort([("item.upload_time", 1)])
	videos = result.skip(page_idx * page_size).limit(page_size)
	video_count = videos.count()
	videos = [i for i in videos]
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
	return videos, video_count
