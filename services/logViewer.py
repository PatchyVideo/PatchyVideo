
from db import db, tagdb
from utils.exceptions import UserError
from datetime import timedelta
from bson import ObjectId

def viewLogs(page_idx, page_size, date_from = None, date_to = None, order = 'latest') :
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
	return [i for i in db.logs.find(date_obj).sort([sort_obj]).skip(page_idx * page_size).limit(page_size)]

def viewLogsAggregated(page_idx, page_size, date_from = None, date_to = None, order = 'latest') :
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
	#TODO: replace this with periodically aggregate logs to a new collection
	ret = db.logs.aggregate([
		{'$match': date_obj},
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
		{'$match':{ 'vid': ObjectId(vid)}},
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
