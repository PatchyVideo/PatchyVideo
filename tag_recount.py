
from db import db, client, tagdb, playlist_db
from utils.dbtools import MongoTransaction
from bson import ObjectId
from collections import defaultdict

if __name__ == '__main__' :
	tag_count_map = defaultdict(int)
	for item in tagdb.db.videos.find({}).batch_size(1000) :
		for tag in item['tags'] :
			if tag < 0x80000000 :
				tag_count_map[tag] += 1
	for tag, count in tag_count_map.items() :
		db.tags.update_one({'id': tag}, {'$set': {'count': count}})
