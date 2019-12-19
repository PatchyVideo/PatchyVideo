
from db import db
from utils.exceptions import UserError
from datetime import timedelta

def viewLogs(page_idx, page_size, date_from = None, date_to = None, order = 'latest') :
	if order not in ['latest', 'oldest'] :
		raise UserError('INCORRECT_ORDER')
	if order == 'latest':
		sort_obj = {"time" : 1}
	if order == 'oldest':
		sort_obj = {"time" : -1}
	if date_from and date_to :
		date_obj = {'time': {'$gte': date_from, '$lt': date_to + timedelta(days = 1)}}
	elif date_from :
		date_obj = {'time': {'$gte': date_from}}
	elif date_to :
		date_obj = {'time': {'$lt': date_to + timedelta(days = 1)}}
	else :
		date_obj = {}
	ret = db.logs.aggregate([
		{'$match': date_obj},
		{'$lookup': {'from': 'logs', 'let': {'event_id': '$_id'}, 'pipeline':[{'$match': {'$expr': {'$eq': ["$id", "$$event_id"]}}}, sort_obj], 'as': 'subevents'}},
		{'$sort': sort_obj},
		{'$skip': page_idx * page_size},
		{'$limit': page_size}
	])
	return ret
