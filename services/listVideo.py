
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

def listVideoQuery(user, query_str, page_idx, page_size, order = 'latest', user_language = 'CHS', hide_placeholder = True):
	log(obj = {'q': query_str, 'page': page_idx, 'page_size': page_size, 'order': order, 'lang': user_language})
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise UserError('INCORRECT_ORDER')
	query_obj, tag_ids = db.compile_query(query_str)
	log(obj = {'query': dumps(query_obj)})
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}]}
		else :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': user['settings']['blacklist']}}]}
	elif user is None :
		query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}]}
	tag_ids = list(set(tag_ids) - set(default_blacklist_tagids))
	updateTagSearch(tag_ids)
	try :
		result = db.retrive_items(query_obj)
		if order == 'latest':
			result = result.sort([("meta.created_at", -1)])
		if order == 'oldest':
			result = result.sort([("meta.created_at", 1)])
		if order == 'video_latest':
			result = result.sort([("item.upload_time", -1)])
		if order == 'video_oldest':
			result = result.sort([("item.upload_time", 1)])
		ret = result.skip(page_idx * page_size).limit(page_size)
		count = ret.count()
		videos = [item for item in ret]
		videos = filterVideoList(videos, user)
		if hide_placeholder :
			videos = _filterPlaceholder(videos)
	except pymongo.errors.OperationFailure as ex:
		if '$not' in str(ex) :
			raise UserError('FAILED_NOT_OP')
		else :
			log(level = 'ERR', obj = {'ex': str(ex)})
			raise UserError('FAILED_UNKNOWN')
	return videos, getCommonTags(user_language, videos), count

def listVideo(page_idx, page_size, user, order = 'latest', user_language = 'CHS', hide_placeholder = True):
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise UserError('INCORRECT_ORDER')
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			query_obj = {'tags': {'$nin': default_blacklist_tagids}}
		else :
			query_obj = {'tags': {'$nin': user['settings']['blacklist']}}
	elif user is None :
		query_obj = {}
	result = db.retrive_items(query_obj)
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
	if hide_placeholder :
		videos = _filterPlaceholder(videos)
	return videos, video_count, getPopularTags(user_language)

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
	return videos, video_count
