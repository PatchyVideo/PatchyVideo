
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, makeUserMetaObject, MongoTransaction
from utils.rwlock import usingResource, modifyingResource

from spiders import dispatch
from db import tagdb, db, client

from datetime import datetime
from bson import ObjectId
from config import PlaylistConfig

import redis_lock

def getPlaylist(pid) :
	return db.playlists.find_one({'_id': ObjectId(pid)})

def _is_authorised(pid_or_obj, user, op = 'edit') :
	if isinstance(pid_or_obj, str) :
		obj = db.playlists.find_one({'_id': ObjectId(pid_or_obj)})
	else :
		obj = pid_or_obj
	creator = str(obj['meta']['created_by'])
	user_id = str(user['_id'])
	return creator == user_id or (op + 'Playlist' in user['access_control']['allowed_ops']) or user['access_control']['status'] == 'admin'

def createPlaylist(language, title, desc, cover, user) :
	obj = {"title": {language: title}, "desc": {language: desc}, "views": 0, "videos": 0, "cover": cover, "meta": makeUserMetaObject(user)}
	pid = db.playlists.insert_one(obj)
	return str(pid.inserted_id)

def createPlaylistFromSingleVideo(language, vid, user) :
	video_obj = tagdb.retrive_item(ObjectId(vid))
	if video_obj is None :
		return "VIDEO_NOT_EXIST"
	new_playlist_id = createPlaylist(language, video_obj['item']['title'], video_obj['item']['desc'], video_obj['item']['cover_image'], user)
	ret = addVideoToPlaylist(new_playlist_id, vid, user)
	return ret, new_playlist_id

def removePlaylist(pid, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(pid, user, 'remove') :
			return "UNAUTHORISED_OPERATION"
		db.playlist_items.delete_many({"pid": ObjectId(pid)}, session = s())
		db.playlists.delete_one({"_id": ObjectId(pid)}, session = s())
		s.mark_succeed()
		return "SUCCEED"

def updatePlaylistCover(pid, cover, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(pid, user) :
			return "UNAUTHORISED_OPERATION"
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {"cover": cover}}, session = s())
		if user is not None :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': ObjectId(user['_id']),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': '',
				'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()
		return "SUCCEED"


def updatePlaylistCoverVID(pid, vid, page, page_size, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
			return "PLAYLIST_NOT_EXIST", None
		if not _is_authorised(pid, user) :
			return "UNAUTHORISED_OPERATION", None
		video_obj = tagdb.retrive_item({"_id": ObjectId(vid)})
		if video_obj is None :
			return "VIDEO_NOT_EXIST", None
		cover = video_obj['item']['cover_image']
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {"cover": cover}}, session = s())
		if user is not None :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': ObjectId(user['_id']),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': '',
				'meta.modified_at': datetime.now()}}, session = s())
		_, video_page, video_count = listPlaylistVideos(pid, page - 1, page_size)
		s.mark_succeed()
		return "SUCCEED", {'videos': video_page, 'video_count': video_count, 'page': page}

def updatePlaylistInfo(pid, language, title, desc, cover, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(pid, user) :
			return "UNAUTHORISED_OPERATION"
		if cover :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {"cover": cover}}, session = s())
		if user is not None :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				"title.%s" % language: title,
				"desc.%s" % language: desc,
				'meta.modified_by': ObjectId(user['_id']),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				"title.%s" % language: title,
				"desc.%s" % language: desc,
				'meta.modified_by': '',
				'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()
		return "SUCCEED"

def addVideoToPlaylist(pid, vid, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(playlist, user) :
			return "UNAUTHORISED_OPERATION"
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			return "VIDEO_NOT_EXIST"
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			return "VIDEO_LIMIT_EXCEEDED"
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			return "VIDEO_ALREADY_EXIST"
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": playlist["videos"], "meta": makeUserMeta(user)}, session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		if user is not None :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': ObjectId(user['_id']),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': '',
				'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()
		return "SUCCEED"

def addVideoToPlaylistLockFree(pid, vid, user) :
	with MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(playlist, user) :
			return "UNAUTHORISED_OPERATION"
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			return "VIDEO_NOT_EXIST"
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			return "VIDEO_LIMIT_EXCEEDED"
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			return "VIDEO_ALREADY_EXIST"
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": playlist["videos"], "meta": makeUserMeta(user)}, session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		if user is not None :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': ObjectId(user['_id']),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': '',
				'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()
		return "SUCCEED"

def listPlaylistVideosWithAuthorizationInfo(pid, page_idx, page_size, user) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		return "PLAYLIST_NOT_EXIST", None, 0
	ans_obj = db.playlist_items.aggregate([
		{
			'$match': {
				"pid": ObjectId(pid)
			}
		},
		{
			'$lookup': {
				'from': "items",
				'localField': "vid",
				'foreignField': "_id",
				'as': 'item'
			}
		},
		{
			'$unwind': {
				'path': '$item'
			}
		},
		{
			'$sort' : {
				'rank' : 1
			}
		},
		{
			'$skip' : page_idx * page_size,
		},
		{
			'$limit' : page_size
		}
	])
	ret = []
	for obj in ans_obj:
		ret_obj = obj['item']
		ret_obj['rank'] = obj['rank']
		ret.append(ret_obj)
	return "SUCCEED", ret, playlist['videos'], _is_authorised(playlist, user)

def listPlaylistVideos(pid, page_idx, page_size) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		return "PLAYLIST_NOT_EXIST", None, 0
	ans_obj = db.playlist_items.aggregate([
		{
			'$match': {
				"pid": ObjectId(pid)
			}
		},
		{
			'$lookup': {
				'from': "items",
				'localField': "vid",
				'foreignField': "_id",
				'as': 'item'
			}
		},
		{
			'$unwind': {
				'path': '$item'
			}
		},
		{
			'$sort' : {
				'rank' : 1
			}
		},
		{
			'$skip' : page_idx * page_size,
		},
		{
			'$limit' : page_size
		}
	])
	ret = []
	for obj in ans_obj:
		ret_obj = obj['item']
		ret_obj['rank'] = obj['rank']
		ret.append(ret_obj)
	return "SUCCEED", ret, playlist['videos']

def listAllPlaylistVideosUnordered(pid) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		return "PLAYLIST_NOT_EXIST", None, 0
	ans_obj = db.playlist_items.find({"pid": ObjectId(pid)})
	return "SUCCEED", [ObjectId(item['vid']) for item in ans_obj], playlist['videos']

def listPlaylists(page_idx, page_size, query = {}, order = 'latest') :
	sort_obj = { "meta.created_at" : 1 }
	if order == 'latest':
		sort_obj = { "meta.created_at" : 1 }
	if order == 'oldest':
		sort_obj = { "meta.created_at" : -1 }
	if order == 'views':
		sort_obj = { "views" : 1 }
	ans_obj = db.playlists.aggregate([
	{
		"$match" : query
	},
	{
		"$lookup" : {
			"from" : "users",
			"localField" : "meta.created_by",
			"foreignField" : "_id",
			"as" : "user_detail"
		}
	},
	{
		"$unwind" : {
			"path" : "$user_detail"
		}
	},
	{
		"$sort" : sort_obj
	},
	{
		'$skip' : page_idx * page_size,
	},
	{
		'$limit' : page_size
	}])
	
	return "SUCCEED", ans_obj, db.playlists.find(query).count()

@usingResource('tags')
def listCommonTags(pid) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		return "PLAYLIST_NOT_EXIST", None
	result = db.playlist_items.aggregate([
	{
		"$match" : {
			"pid" : ObjectId(pid)
		}
	},
	{
		"$lookup" : {
			"from" : "items",
			"localField" : "vid",
			"foreignField" : "_id",
			"as" : "video"
		}
	},
	{
		"$project" : {
			"video.tags" : 1
		}
	},
	{
		"$unwind" : {
			"path" : "$video"
		}
	},
	{
		"$project" : {
			"tags" : "$video.tags"
		}
	},
	{
		"$group" : {
			"_id" : 0,
			"tags" : {
				"$push" : "$tags"
			},
			"initialTags" : {
				"$first" : "$tags"
			}
		}
	},
	{
		"$project" : {
			"commonTags" : {
				"$reduce" : {
					"input" : "$tags",
					"initialValue" : "$initialTags",
					"in" : {
						"$setIntersection" : [
							"$$value",
							"$$this"
						]
					}
				}
			}
		}
	}
	])
	ret = [i for i in result]
	if ret :
		ret = ret[0]['commonTags']
		return 'SUCCEED', ret
	else :
		return 'SUCCEED', []

@usingResource('tags')
def updateCommonTags(pid, tags, user) :
	with MongoTransaction(client) as s :
		if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
			return "PLAYLIST_NOT_EXIST"
		# user is editing video tags, not the playlist itself, no need to lock playlist or check for authorization
		_, old_tags = listCommonTags(pid)
		old_tags_set = set(old_tags)
		new_tags_set = set(tags)
		tags_added = list((old_tags_set ^ new_tags_set) - old_tags_set)
		tags_added = tagdb.filter_tags(tags_added)
		tags_added = tagdb.translate_tags(tags_added)
		tags_to_remove = list((old_tags_set ^ new_tags_set) - new_tags_set)
		if len(tags_added) - len(tags_to_remove) > PlaylistConfig.MAX_COMMON_TAGS :
			return 'TOO_MANY_TAGS'
		ret, all_video_ids, _ = listAllPlaylistVideosUnordered(pid)
		if ret != 'SUCCEED' :
			return ret
		if tags_to_remove :
			tagdb.update_many_items_tags_pull(all_video_ids, tags_to_remove, makeUserMeta(user), session = s())
		if tags_added :
			tagdb.update_many_items_tags_merge(all_video_ids, tags_added, makeUserMeta(user), session = s())
		s.mark_succeed()
		return 'SUCCEED'


def listPlaylistsForVideo(vid) :
	video = tagdb.retrive_item({'_id': ObjectId(vid)})
	if video is None :
		return "VIDEO_NOT_EXIST"
	result = db.playlist_items.aggregate([
		{
			'$match': {
				'$and': [
				{
					'pid': {
						'$in': video['item']['series']
					}
				},
				{
					'vid': video['_id']
				}]
			}
		},
		{
			'$lookup': {
				'from': 'playlists',
				'localField': 'pid',
				'foreignField': '_id',
				'as': 'playlist'
			}
		},
		{
			'$unwind': {
				'path': '$playlist'
			}
		}
	])
	ans = []
	for obj in result :
		playlist_obj = obj['playlist']
		playlist_obj['prev'] = ''
		playlist_obj['next'] = ''
		rank = obj['rank']
		if rank > 0 :
			playlist_obj['prev'] = str(db.playlist_items.find_one({'$and': [{'pid': playlist_obj['_id']}, {'rank': rank - 1}]})['vid'])
		if rank + 1 < playlist_obj['videos'] :
			playlist_obj['next'] = str(db.playlist_items.find_one({'$and': [{'pid': playlist_obj['_id']}, {'rank': rank + 1}]})['vid'])
		ans.append(playlist_obj)
	return ans

def removeVideoFromPlaylist(pid, vid, page, page_size, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(playlist, user) :
			return "UNAUTHORISED_OPERATION"
		if playlist["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				return "VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST"
			db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gt': entry['rank']}}]}, {'$inc': {'rank': -1}}, session = s())
			db.playlist_items.delete_one({'_id': entry['_id']}, session = s())
			db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": -1}}, session = s())
			if user is not None :
				db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
					'meta.modified_by': ObjectId(user['_id']),
					'meta.modified_at': datetime.now()}}, session = s())
			else :
				db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
					'meta.modified_by': '',
					'meta.modified_at': datetime.now()}}, session = s())
		else :
			return "EMPTY_PLAYLIST"
		_, video_page, video_count = listPlaylistVideos(pid, page - 1, page_size)
		if len(video_page) == 0 and page > 1 and video_count > 0 :
			# in case deleting video results in current page becomes empty, show the previous page
			_, video_page, video_count = listPlaylistVideos(pid, page - 2, page_size)
			s.mark_succeed()
			return "SUCCEED", {'videos': video_page, 'video_count': video_count, 'page': page - 1}
		s.mark_succeed()
		return "SUCCEED", {'videos': video_page, 'video_count': video_count, 'page': page}

def editPlaylist_MoveUp(pid, vid, page, page_size, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			return "PLAYLIST_NOT_EXIST", None
		if not _is_authorised(playlist, user) :
			return "UNAUTHORISED_OPERATION", None
		if playlist["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				s.mark_failover()
				return "VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST", None
			if entry['rank'] <= 0 :
				return "SUCCEED", None
			exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": entry['rank'] - 1}, session = s())
			db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': entry['rank'] - 1}}, session = s())
			db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': entry['rank']}}, session = s())
			if user is not None :
				db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
					'meta.modified_by': ObjectId(user['_id']),
					'meta.modified_at': datetime.now()}}, session = s())
			else :
				db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
					'meta.modified_by': '',
					'meta.modified_at': datetime.now()}}, session = s())
			_, video_page, video_count = listPlaylistVideos(pid, page - 1, page_size)
			s.mark_succeed()
			return "SUCCEED", {'videos': video_page, 'video_count': video_count, 'page': page}
		else :
			return "EMPTY_PLAYLIST", None

def editPlaylist_MoveDown(pid, vid, page, page_size, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			return "PLAYLIST_NOT_EXIST", None
		if not _is_authorised(playlist, user) :
			return "UNAUTHORISED_OPERATION", None
		if playlist["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				return "VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST", None
			if entry['rank'] >= playlist["videos"] - 1 :
				return "SUCCEED", None
			exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": entry['rank'] + 1}, session = s())
			db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': entry['rank'] + 1}}, session = s())
			db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': entry['rank']}}, session = s())
			if user is not None :
				db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
					'meta.modified_by': ObjectId(user['_id']),
					'meta.modified_at': datetime.now()}}, session = s())
			else :
				db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
					'meta.modified_by': '',
					'meta.modified_at': datetime.now()}}, session = s())
			_, video_page, video_count = listPlaylistVideos(pid, page - 1, page_size)
			s.mark_succeed()
			return "SUCCEED", {'videos': video_page, 'video_count': video_count, 'page': page}
		else :
			return "EMPTY_PLAYLIST", None

def insertIntoPlaylist(pid, vid, rank, user) :
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(playlist, user) :
			return "UNAUTHORISED_OPERATION"
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			return "VIDEO_NOT_EXIST"
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			return "VIDEO_LIMIT_EXCEEDED"
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			return "VIDEO_ALREADY_EXIST"
		if rank < 0 :
			return "OUT_OF_RANGE"
		if rank > playlist['videos'] :
			rank = playlist['videos']
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gte': rank}}]}, {'$inc': {'rank': 1}}, session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": rank, "meta": makeUserMeta(user)}, session = s())
		if user is not None :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': ObjectId(user['_id']),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': '',
				'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()
		return "SUCCEED"

def insertIntoPlaylistLockFree(pid, vid, rank, user) :
	with MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			return "PLAYLIST_NOT_EXIST"
		if not _is_authorised(playlist, user) :
			return "UNAUTHORISED_OPERATION"
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			return "VIDEO_NOT_EXIST"
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			return "VIDEO_LIMIT_EXCEEDED"
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			return "VIDEO_ALREADY_EXIST"
		if rank < 0 :
			return "OUT_OF_RANGE"
		if rank > playlist['videos'] :
			rank = playlist['videos']
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gte': rank}}]}, {'$inc': {'rank': 1}}, session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": rank, "meta": makeUserMeta(user)}, session = s())
		if user is not None :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': ObjectId(user['_id']),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': '',
				'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()
		return "SUCCEED"
