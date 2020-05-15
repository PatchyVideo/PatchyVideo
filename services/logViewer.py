
from db import db, tagdb
from utils.exceptions import UserError
from datetime import timedelta
from datetime import datetime
from bson import ObjectId

def viewLogs(page_idx, page_size, date_from = None, date_to = None, order = 'latest', op = '', level = ['MSG', 'WARN', 'SEC', 'ERR']) :
	if order not in ['latest', 'oldest'] :
		raise UserError('INCORRECT_ORDER')
	if order == 'latest':
		sort_obj = ("time", -1)
	if order == 'oldest':
		sort_obj = ("time", 1)
	if date_from and date_to :
		date_obj = {'time': {'$gte': date_from, '$lt': date_to + timedelta(days = 1)}}
	elif date_from :
		date_obj = {'time': {'$gte': date_from}}
	elif date_to :
		date_obj = {'time': {'$lt': date_to + timedelta(days = 1)}}
	else :
		date_obj = {}
	date_obj = {'$and': [date_obj, {'level': {'$in': level}}]}
	if op :
		date_obj['$and'].append({'op': op})
	return [i for i in db.logs.find(date_obj).sort([sort_obj]).skip(page_idx * page_size).limit(page_size)]

def viewLogsAggregated(page_idx, page_size, date_from = None, date_to = None, order = 'latest', op = '', level = ['MSG', 'WARN', 'SEC', 'ERR']) :
	if order not in ['latest', 'oldest'] :
		raise UserError('INCORRECT_ORDER')
	if order == 'latest':
		sort_obj = {"time": -1}
	if order == 'oldest':
		sort_obj = {"time": 1}
	if date_from and date_to :
		date_obj = {'time': {'$gte': date_from, '$lt': date_to + timedelta(days = 1)}}
	elif date_from :
		date_obj = {'time': {'$gte': date_from}}
	elif date_to :
		date_obj = {'time': {'$lt': date_to + timedelta(days = 1)}}
	else :
		date_obj = {}
	date_obj2 = {'$and': [date_obj, {'level': {'$in': level}}]}
	if op :
		date_obj2['$and'].append({'op': op})
	#TODO: replace this with periodically aggregate logs to a new collection
	ret = db.logs.aggregate([
		{'$match': date_obj2},
		{'$sort': sort_obj},
		#{'$skip': page_idx * page_size},
		{'$limit': page_size * 20},
		{'$lookup': {'from': 'logs', 'let': {'event_id': '$_id', 'time': '$time'}, 'pipeline':[
			{'$match': date_obj},
			{'$sort': sort_obj},
			#{'$skip': page_idx * page_size},
			{'$limit': page_size * 20},
			{'$match': {'$expr': {'$eq': ["$id", "$$event_id"]}}},
			], 'as': 'subevents'}},
		{'$limit': page_size}
	])
	return [i for i in ret]

def viewTaghistory(vid, language) :
	all_items = db.tag_history.aggregate([
		{'$match': {'vid': ObjectId(vid)}},
		{'$lookup': {'from': 'users', 'localField': 'user', 'foreignField': '_id', 'as': 'user_obj'}},
		{'$project': {'user_obj._id': 1, 'user_obj.profile.username': 1, 'user_obj.profile.image': 1, 'tags': 1, 'del': 1, 'add': 1, 'time': 1}},
		{'$sort': {"time": -1}}
	])
	all_items = list(all_items)
	for item in all_items :
		item['tags'], _, _ = tagdb.translate_tag_ids_to_user_language(item['tags'], language)
		item['del'], _, _ = tagdb.translate_tag_ids_to_user_language(item['del'], language)
		item['add'], _, _ = tagdb.translate_tag_ids_to_user_language(item['add'], language)
	return all_items

def rankTagContributor(hrs = 24, n = 20) :
	"""
	List top `n` user who contibuted the most tag updates in the last `hrs` hours
	"""
	cur_time = datetime.now()
	ans = db.tag_history.aggregate([
		{'$match': {'time': {'$gte': cur_time - timedelta(hours = hrs)}}},
		{'$match': {'$or': [{'add': {'$not': {'$size': 0}}}, {'del': {'$not': {'$size': 0}}}]}},
		{'$group': {'_id': '$user', 'count': {'$sum': 1}}},
		{'$sort': {'count': -1}},
		{'$limit': n},
		{'$lookup': {'from': 'users', 'localField': '_id', 'foreignField': '_id', 'as': 'user_obj'}},
		{'$unwind': {'path': '$user_obj'}},
		{'$project': {'user_obj._id': 1, 'user_obj.profile.username': 1, 'user_obj.profile.desc': 1, 'user_obj.profile.image': 1, 'count': 1}}
	])
	return list(ans)

def viewRawTagHistory(page, page_size, language) :
	all_items = db.tag_history.aggregate([
		{'$sort': {"time": -1}},
		{'$skip': page * page_size},
		{'$limit': page_size},
		{'$lookup': {'from': 'users', 'localField': 'user', 'foreignField': '_id', 'as': 'user_obj'}},
		{'$project': {'vid': 1, 'user_obj._id': 1, 'user_obj.profile.username': 1, 'user_obj.profile.image': 1, 'tags': 1, 'del': 1, 'add': 1, 'time': 1}},
		{'$lookup': {'from': 'videos', 'localField': 'vid', 'foreignField': '_id', 'as': 'video_obj'}},
		{'$project': {
			'vid': 1,
			'user_obj._id': 1,
			'user_obj.profile.username': 1,
			'user_obj.profile.image': 1,
			'tags': 1,
			'del': 1,
			'add': 1,
			'time': 1,
			'video_obj.item': 1
			}
		},
	])
	all_items = list(all_items)
	for item in all_items :
		item['tags'], _, _ = tagdb.translate_tag_ids_to_user_language(item['tags'], language)
		item['del'], _, _ = tagdb.translate_tag_ids_to_user_language(item['del'], language)
		item['add'], _, _ = tagdb.translate_tag_ids_to_user_language(item['add'], language)
	return all_items
