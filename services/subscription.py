
from bson import ObjectId
from datetime import datetime

from db import tagdb, db
from utils.exceptions import UserError
from utils.dbtools import makeUserMetaObject, makeUserMeta
from .tagStatistics import getPopularTags, getCommonTags, updateTagSearch
from services.tcb import filterVideoList
from services.config import Config

def addSubscription(user, query_str : str, qtype = 'tag', name = '') :
	query_str = query_str.strip()
	if not query_str :
		raise UserError('EMPTY_QUERY')
	# TODO: add duplicated query check
	qobj, qtags = tagdb.compile_query(query_str, qtype)
	if len(qtags) == 1 and 'tags' in qobj :
		subid = db.subs.insert_one({'qs': query_str, 'qt': qtype, 'name': name, 'tagid': qobj['tags'], 'meta': makeUserMetaObject(user)}).inserted_id
	else :
		subid = db.subs.insert_one({'qs': query_str, 'qt': qtype, 'name': name, 'meta': makeUserMetaObject(user)}).inserted_id
	return str(subid)

def listSubscriptions(user) :
	return list(db.subs.find({'meta.created_by': makeUserMeta(user)}))

def listSubscriptionTags(user) :
	return list(db.subs.find({'meta.created_by': makeUserMeta(user), 'tagid': {'$exists': True}}))

def removeSubScription(user, sub_id) :
	obj = db.subs.find_one({'_id': ObjectId(sub_id)})
	if obj is None :
		raise UserError('SUB_NOT_EXIST')
	db.subs.delete_one({'_id': ObjectId(sub_id)})

def updateSubScription(user, sub_id, query_str : str, qtype : str = '', name = '') :
	obj = db.subs.find_one({'_id': ObjectId(sub_id)})
	if obj is None :
		raise UserError('SUB_NOT_EXIST')
	# TODO: add duplicated query check
	tagdb.compile_query(query_str, qtype)
	if not name :
		name = obj['name']
	if not qtype :
		qtype = obj['qt']
	db.subs.update_one({'_id': ObjectId(sub_id)}, {'$set': {
		'qs': query_str,
		'qt': qtype,
		'name': name,
		'meta.modified_by': makeUserMeta(user),
		'meta.modified_at': datetime.now()
	}})

def _filterPlaceholder(videos) :
	return list(filter(lambda x: not ('placeholder' in x['item'] and x['item']['placeholder']), videos))

def listSubscriptedItems(user, page_idx, page_size, user_language, hide_placeholder = True, order = 'latest_video') :
	subs = list(db.subs.find({'meta.created_by': makeUserMeta(user)}))
	q = [tagdb.compile_query(q['qs'], q['qt']) for q in subs]
	query_obj = {'$or': []}
	for qi, _ in q :
		query_obj['$or'].append(qi)
	for i in range(len(q)) :
		subs[i]['obj'] = q[i][0]
		subs[i]['obj_tags'] = q[i][1]
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}]}
		else :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': user['settings']['blacklist']}}]}
	elif user is None :
		query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}]}
	result = tagdb.retrive_items(query_obj)
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
	return videos, subs, getCommonTags(user_language, videos), count
