
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
	if len(qtags) == 1 and 'tags' in qobj and isinstance(qobj['tags'], int) and qobj['tags'] < 0x80000000:
		subid = db.subs.insert_one({'qs': query_str.strip(), 'qt': qtype, 'name': name, 'tagid': qobj['tags'], 'meta': makeUserMetaObject(user)}).inserted_id
	else :
		subid = db.subs.insert_one({'qs': query_str, 'qt': qtype, 'name': name, 'meta': makeUserMetaObject(user)}).inserted_id
	return str(subid)

def listSubscriptions(user) :
	return list(db.subs.find({'meta.created_by': makeUserMeta(user)}))

def listSubscriptionTags(user, language = 'CHS') :
	ret = list(db.subs.find({'meta.created_by': makeUserMeta(user), 'tagid': {'$exists': True}}))
	return tagdb.translate_tag_ids_to_user_language([x['tagid'] for x in ret], language)[0]

def removeSubScription(user, sub_id) :
	obj = db.subs.find_one({'_id': ObjectId(sub_id)})
	if obj is None :
		raise UserError('SUB_NOT_EXIST')
	db.subs.delete_one({'_id': ObjectId(sub_id)})

def removeTagSubScription(user, tags) :
	if isinstance(tags, str) :
		tags = [tags]
	tagids = tagdb.translate_tags([x.strip() for x in tags])
	db.subs.delete_many({'tagid': {'$in': tagids}})

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

def listSubscriptedItems(user, offset, limit, user_language, hide_placeholder = True, order = 'video_latest', visibleSubs = [''], additional_constraint = '') :
	subs = list(db.subs.find({'meta.created_by': makeUserMeta(user)}))
	q = [(tagdb.compile_query(q['qs'], q['qt']), str(q['_id'])) for q in subs]
	query_obj = {'$or': []}
	if '' in visibleSubs :
		for (qi, _), _ in q :
			query_obj['$or'].append(qi)
	else :
		for (qi, _), qid in q :
			if qid in visibleSubs :
				query_obj['$or'].append(qi)
	for i in range(len(q)) :
		(qobj, qtags), _ = q[i]
		subs[i]['obj'] = qobj
		subs[i]['obj_tags'] = qtags
	if not query_obj['$or'] :
		return [], subs, [], 0
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	query_obj_extra, _ = tagdb.compile_query(additional_constraint, 'tag')
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
		else :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': user['settings']['blacklist']}}, query_obj_extra]}
	elif user is None :
		query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
	result = tagdb.retrive_items(query_obj)
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
	count = ret.count()
	videos = [item for item in ret]
	videos = filterVideoList(videos, user)
	if hide_placeholder :
		videos = _filterPlaceholder(videos)
	return videos, subs, *getCommonTags(user_language, videos), count

def listSubscriptedItemsRandomized(user, limit, user_language, visibleSubs = [''], additional_constraint = '') :
	subs = list(db.subs.find({'meta.created_by': makeUserMeta(user)}))
	q = [(tagdb.compile_query(q['qs'], q['qt']), str(q['_id'])) for q in subs]
	query_obj = {'$or': []}
	if '' in visibleSubs :
		for (qi, _), _ in q :
			query_obj['$or'].append(qi)
	else :
		for (qi, _), qid in q :
			if qid in visibleSubs :
				query_obj['$or'].append(qi)
	for i in range(len(q)) :
		(qobj, qtags), _ = q[i]
		subs[i]['obj'] = qobj
		subs[i]['obj_tags'] = qtags
	if not query_obj['$or'] :
		return [], subs, []
	default_blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST.split(',')]
	query_obj_extra, _ = tagdb.compile_query(additional_constraint, 'tag')
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
		else :
			query_obj = {'$and': [query_obj, {'tags': {'$nin': user['settings']['blacklist']}}, query_obj_extra]}
	elif user is None :
		query_obj = {'$and': [query_obj, {'tags': {'$nin': default_blacklist_tagids}}, query_obj_extra]}
	videos = list(tagdb.aggregate([
		{'$match': query_obj},
		{'$sample': {'size': limit * 2}}
	]))
	videos = filterVideoList(videos, user)
	for i in range(len(videos)) :
		videos[i]['tags'] = list(filter(lambda x: x < 0x80000000, videos[i]['tags']))
	videos = _filterPlaceholder(videos)
	videos = videos[: limit]
	return videos, subs, *getCommonTags(user_language, videos)
