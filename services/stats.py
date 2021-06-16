
import pymongo
from db import db

def _to_id_popularity(item) :
	return {
		'id': item['id'],
		'count': item['count']
	}

def site_stats() :
	registered_users = db.users.count_documents({})
	top_tag_ids = [_to_id_popularity(i) for i in db.tags.find({}).sort([('count', pymongo.DESCENDING)]).limit(20)]
	return registered_users, top_tag_ids
