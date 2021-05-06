

from db import db, client, tagdb, playlist_db
from utils.dbtools import MongoTransaction
from bson import ObjectId

'''
if __name__ == '__main__' :
	with MongoTransaction(client) as s :
		for item in [i for i in db.videos.find({'item.cover_image':'','item.site':'youtube'},session=s())]:
			print('Updating %s'%item['item']['unique_id'])
			yid = item['item']['unique_id'].split(':')[1]
			data = {
				'title':item['item']['title'],
				'desc':item['item']['desc'],
				'site':item['item']['site'],
				'unique_id':item['item']['unique_id'],
				'thumbnailURL':"https://img.youtube.com/vi/%s/hqdefault.jpg"%yid,
				}
			new_data = _make_video_data(data,item['item']['copies'],item['item']['series'],item['item']['url'])
			db.videos.update_one({'_id':ObjectId(item['_id'])},{'$set':{
				'item.cover_image':new_data['cover_image'],
				'item.thumbnail_url':new_data['thumbnail_url']}},session=s())
				
			print('New image:%s'%new_data['cover_image'])
		s.mark_succeed()

'''

"""
if __name__ == '__main__' :
	with MongoTransaction(client) as s :
		all_tags = [t for t in db.tags.find(session = s())]
		all_root_tags = [t for t in db.tags.find({'dst': {'$exists': False}}, session = s()).sort([("meta.created_at", 1)])]
		all_alias_tags = [t for t in db.tags.find({'dst': {'$exists': True}}, session = s())]
		db.tags.delete_many({}, session = s())
		db.cats.update_many({}, {'$set': {'count': 0}}, session = s())
		tag_map = {}
		for rt in all_root_tags :
			tag_id = tagdb.add_tag(rt['tag'], rt['category'], rt['language'], session = s())
			tag_map[rt['tag']] = tag_id
			db.tags.update_one({'id': tag_id}, {'$set': {'count': int(rt['count'])}}, session = s())
			print(f"{rt['language']}: {rt['tag']} -> {tag_id}")
		for tt in all_alias_tags :
			if tt['type'] == 'language' :
				tagdb.add_or_rename_tag(tt['dst'], tt['tag'], tt['language'], session = s())
				print(f"{tt['language']}: {tt['tag']} -> {tt['dst']}")
		video_tag_map = {}
		for vid in db.videos.find(session = s()) :
			tag_ids = []
			for t in vid['tags'] :
				if t not in tag_map :
					print(f"!!! tag {t} does not exist for video {vid['_id']} {vid['item']['title']}")
				else :
					tag_ids.append(tag_map[t])
			video_tag_map[str(vid['_id'])] = tag_ids
			#print(f"{vid['tags']} -> {tag_ids}")
		for (_id, tags) in video_tag_map.items() :
			db.videos.update_one({'_id': ObjectId(_id)}, {'$set': {'tags': tags}}, session = s())
		s.mark_succeed()
"""

"""
if __name__ == '__main__' :
	cursor = db.videos.find(no_cursor_timeout = True).batch_size(100)
	for item in cursor :
		db.tag_history.insert_one({
			'vid': item['_id'],
			'user': item['meta']['created_by'],
			'tags': [],
			'add': list(filter(lambda x: x < 0x80000000, item['tags'])),
			'del': [],
			'time': item['meta']['created_at']
		})
"""

"""
if __name__ == '__main__' :
	from db.index.index_builder import build_index
	#with MongoTransaction(client) as s :
	db.videos.update_many({}, {'$pull': {'tags': {'$gte': 0x80000000}}})
	db.index_words.delete_many({})
	#    s.mark_succeed()
	cursor = db.videos.find(no_cursor_timeout = True).batch_size(100)
	#with MongoTransaction(client) as s :
	for item in cursor :
		print(item['item']['title'])
		word_ids = build_index([item['item']['desc'], item['item']['title']])
		db.videos.update_one({'_id': item['_id']}, {'$set': {'tags': item['tags'] + word_ids}})
	#    s.mark_succeed()
"""

"""
if __name__ == '__main__' :
	cursor = db.videos.find({'item.site': 'bilibili'}, no_cursor_timeout = True).batch_size(100)
	for item in cursor :
		print(item['item']['title'])
		db.videos.update_one({'_id': item['_id']}, {'$set': {'item.unique_id': item['item']['unique_id'] + '-1'}})
		db.videos.update_one({'_id': item['_id']}, {'$set': {'item.url': item['item']['url'] + '?p=1'}})
"""

"""
if __name__ == '__main__' :
	cursor = db.playlists.find({}, no_cursor_timeout = True).batch_size(100)
	for item in cursor :
		title = item['title']['english']
		desc = item['desc']['english']
		cover = item['cover']
		private = item['private']
		views = item['views']
		videos = item['videos']
		total_rating = item['total_rating']
		total_rating_user = item['total_rating_user']
		print(title)
		new_id = playlist_db.add_item([],
		{
			"title": title,
			"desc": desc,
			"private": private,
			"views": views,
			"videos": videos,
			"cover": cover
		},
		3,
		['title', 'desc'],
		'',
		None,
		id_override = item['_id']
		)
		assert str(new_id) == str(item['_id'])
		db.playlist_metas.update_one({'_id': item["_id"]}, {'$set': {'meta': item['meta']}})
"""

"""
if __name__ == '__main__' :
	kkhta_1 = db.videos.find_one({"item.unique_id":"bilibili:av92261-1"})
	video_data = kkhta_1['item']
	video_data['series'] = []
	video_data['copies'] = []
	for i in range(2, 11) :
		video_data['url'] = 'https://www.bilibili.com/video/av92261?p=%d' % i
		video_data['title'] = '【東方手書】恋恋的♥心♥跳♥大冒险【PART1-10】(part %d)' % i
		video_data['unique_id'] = 'bilibili:av92261-%d' % i
		new_item_id = tagdb.add_item(['已失效视频'], video_data, 3, ['title', 'desc'], kkhta_1['meta']['created_by'])
"""

"""
if __name__ == '__main__' :
	from db.index.index_builder import build_index
	db.index_words.delete_many({})
	db.playlist_metas.update_many({}, {'$pull': {'tags': {'$gte': 0x80000000}}})
	db.videos.update_many({}, {'$pull': {'tags': {'$gte': 0x80000000}}})
	cursor = db.playlist_metas.find(no_cursor_timeout = True).batch_size(100)
	for item in cursor :
		print(item['item']['title'])
		word_ids = build_index([item['item']['desc'], item['item']['title']])
		db.playlist_metas.update_one({'_id': item['_id']}, {'$set': {'tags': item['tags'] + word_ids}})
	cursor = db.videos.find(no_cursor_timeout = True).batch_size(100)
	for item in cursor :
		print(item['item']['title'])
		word_ids = build_index([item['item']['desc'], item['item']['title']])
		db.videos.update_one({'_id': item['_id']}, {'$set': {'tags': item['tags'] + word_ids}})
"""

"""
if __name__ == '__main__' :
	from services.authorDB import createUserSpaceIds
	cursor = db.authors.find(no_cursor_timeout = True).batch_size(100)
	for author in cursor :
		db.authors.update_one({"_id": author["_id"]}, {"$set": {"user_space_ids": createUserSpaceIds(author['urls'])}})
"""

if __name__ == '__main__' :
	users = list(db.users.find({}))
	for u in users :
		uid = u['_id']
		if 'email' in u['profile'] and u['profile']['email'] :
			email = u['profile']['email'].lower()
			db.users.update_one({'_id': uid}, {'$set': {'profile.email': email}})
