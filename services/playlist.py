
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, makeUserMetaObject, MongoTransaction
from utils.rwlock import usingResource, modifyingResource
from utils.exceptions import UserError

from spiders import dispatch
from db import tagdb, db, client

from datetime import datetime
from bson import ObjectId
from config import PlaylistConfig
from utils.logger import log
from services.tcb import filterSingleVideo, filterVideoList, filterOperation

import redis_lock

def getPlaylist(pid) :
	ret = db.playlists.find_one({'_id': ObjectId(pid)})
	if not ret :
		raise UserError('PLAYLIST_NOT_EXIST')
	return ret

def _is_authorised(pid_or_obj, user, op = 'edit') :
	if isinstance(pid_or_obj, str) :
		obj = db.playlists.find_one({'_id': ObjectId(pid_or_obj)})
	else :
		obj = pid_or_obj
	creator = str(obj['meta']['created_by'])
	user_id = str(user['_id'])
	return creator == user_id or (op + 'Playlist' in user['access_control']['allowed_ops']) or user['access_control']['status'] == 'admin'

def createPlaylist(language, title, desc, cover, user, private = False) :
	log(obj = {'title': title, 'desc': desc, 'cover': cover, 'private': private})
	filterOperation('createPlaylist', user)
	if len(title) > PlaylistConfig.MAX_TITLE_LENGTH :
		raise UserError('TITLE_TOO_LONG')
	if len(desc) > PlaylistConfig.MAX_DESC_LENGTH :
		raise UserError('DESC_TOO_LONG')
	if len(cover) > PlaylistConfig.MAX_COVER_URL_LENGTH :
		raise UserError('URL_TOO_LONG')
	if not title :
		raise UserError('EMPTY_TITLE')
	if not desc :
		raise UserError('EMPTY_DESC')
	obj = {"title": {language: title}, "desc": {language: desc}, "private": private, "views": 0, "videos": 0, "cover": cover, "meta": makeUserMetaObject(user)}
	pid = db.playlists.insert_one(obj)
	log(obj = {'pid': pid.inserted_id})
	return str(pid.inserted_id)

def createPlaylistFromSingleVideo(language, vid, user) :
	log(obj = {'vid': vid})
	filterOperation('createPlaylistFromSingleVideo', user)
	video_obj = filterSingleVideo(vid, user)
	if video_obj is None :
		raise UserError('VIDEO_NOT_EXIST')
	new_playlist_id = createPlaylist(language, video_obj['item']['title'], video_obj['item']['desc'], video_obj['item']['cover_image'], user)
	log(obj = {'pid': new_playlist_id})
	addVideoToPlaylist(new_playlist_id, vid, user)
	return new_playlist_id

def removePlaylist(pid, user) :
	log(obj = {'pid': pid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = db.playlists.find_one({'_id': ObjectId(pid)})
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('removePlaylist', user, list_obj)
		all_items = db.playlist_items.find({"pid": ObjectId(pid)}, session = s())
		log(obj = {'items': [i for i in all_items]})
		db.playlist_items.delete_many({"pid": ObjectId(pid)}, session = s())
		db.playlists.delete_one({"_id": ObjectId(pid)}, session = s())
		s.mark_succeed()

def listMyPlaylists(user, page_idx = 0, page_size = 10000, order = 'last_modified') :
	if order not in ['latest', 'oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	result = db.playlists.find({'meta.created_by': ObjectId(user['_id'])})
	if order == 'last_modified' :
		result = result.sort([("meta.modified_at", -1)])
	if order == 'latest':
		result = result.sort([("meta.created_at", 1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", -1)])
	return result.skip(page_idx * page_size).limit(page_size)

def updatePlaylistCover(pid, cover, user) :
	log(obj = {'pid': pid, 'cover': cover})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = db.playlists.find_one({'_id': ObjectId(pid)})
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('updatePlaylistCover', user, list_obj)
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {"cover": cover}}, session = s())
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()

def updatePlaylistCoverVID(pid, vid, page, page_size, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = db.playlists.find_one({'_id': ObjectId(pid)})
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('updatePlaylistCoverVID', user, list_obj)
		video_obj = filterSingleVideo(vid, user)
		if video_obj is None :
			raise UserError('VIDEO_NOT_EXIST')
		cover = video_obj['item']['cover_image']
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {"cover": cover}}, session = s())
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()}}, session = s())
		video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
		s.mark_succeed()
		return {'videos': video_page, 'video_count': video_count, 'page': page}

def updatePlaylistInfo(pid, language, title, desc, cover, user, private = False) :
	log(obj = {'title': title, 'desc': desc, 'cover': cover, 'private': private})
	if len(title) > PlaylistConfig.MAX_TITLE_LENGTH :
		raise UserError('TITLE_TOO_LONG')
	if len(desc) > PlaylistConfig.MAX_DESC_LENGTH :
		raise UserError('DESC_TOO_LONG')
	if len(cover) > PlaylistConfig.MAX_COVER_URL_LENGTH :
		raise UserError('URL_TOO_LONG')
	if not title :
		raise UserError('EMPTY_TITLE')
	if not desc :
		raise UserError('EMPTY_DESC')
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = db.playlists.find_one({'_id': ObjectId(pid)})
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('updatePlaylistInfo', user, list_obj)
		if cover :
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {"cover": cover}}, session = s())
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
			"title.%s" % language: title,
			"desc.%s" % language: desc,
			"private": private,
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()

def addVideoToPlaylist(pid, vid, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('addVideoToPlaylist', user, playlist)
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			raise UserError('VIDEO_NOT_EXIST')
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			raise UserError('VIDEO_LIMIT_EXCEEDED')
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			raise UserError('VIDEO_ALREADY_EXIST', vid)
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": playlist["videos"], "meta": makeUserMeta(user)}, session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()

def addVideoToPlaylistLockFree(pid, vid, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('addVideoToPlaylist', user, playlist)
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			raise UserError('VIDEO_NOT_EXIST')
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			raise UserError('VIDEO_LIMIT_EXCEEDED')
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			raise UserError('VIDEO_ALREADY_EXIST', vid)
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": playlist["videos"], "meta": makeUserMeta(user)}, session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()

def listPlaylistVideosWithAuthorizationInfo(pid, page_idx, page_size, user) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
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
	ret = filterVideoList(ret, user)
	return ret, playlist['videos'], _is_authorised(playlist, user)

def listPlaylistVideos(pid, page_idx, page_size, user) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
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
	ret = filterVideoList(ret, user)
	return ret, playlist['videos']

def listAllPlaylistVideosUnordered(pid) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
	ans_obj = db.playlist_items.find({"pid": ObjectId(pid)})
	return [ObjectId(item['vid']) for item in ans_obj], playlist['videos']

def listAllPlaylistVideosOrdered(pid) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
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
		}
	])
	return [i for i in ans_obj], playlist['videos'], playlist

def listPlaylists(page_idx, page_size, query = {}, order = 'latest') :
	sort_obj = { "meta.created_at" : 1 }
	if order == 'latest':
		sort_obj = { "meta.created_at" : 1 }
	if order == 'oldest':
		sort_obj = { "meta.created_at" : -1 }
	if order == 'views':
		sort_obj = { "views" : 1 }
	query = {'$and': [query, {'private': False}]}
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
		"$project": {
			"user_detail.crypto": 0,
			"user_detail.access_control": 0,
			"user_detail.meta": 0
		}
	},
	{'$facet':
		{
			'result': [
				{'$sort': sort_obj},
				{'$skip': page_idx * page_size},
				{'$limit': page_size}
			],
			'count': [
				{'$count': 'count'}
			]
		}
	}
	])
	ans_obj = [i for i in ans_obj][0]
	if ans_obj['result'] :
		return [i for i in ans_obj['result']], ans_obj['count'][0]['count']
	else :
		return [], 0

def listCommonTagIDs(pid) :
	playlist = db.playlists.find_one({'_id': ObjectId(pid)})
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
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
		return ret[0]['commonTags']
	else :
		return []

@usingResource('tags')
def listCommonTags(pid, language) :
	return tagdb.translate_tag_ids_to_user_language(listCommonTagIDs(pid), language)[0]

@usingResource('tags')
def updateCommonTags(pid, tags, user) :
	log(obj = {'pid': pid, 'tags': tags})
	filterOperation('updateCommonTags', user, pid)
	with MongoTransaction(client) as s :
		if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		# user is editing video tags, not the playlist itself, no need to lock playlist or check for authorization
		tags = tagdb.filter_and_translate_tags(tags, s())
		old_tags = listCommonTagIDs(pid)
		log(obj = {'old_tags': old_tags})
		old_tags_set = set(old_tags)
		new_tags_set = set(tags)
		tags_added = list((old_tags_set ^ new_tags_set) - old_tags_set)
		tags_to_remove = list((old_tags_set ^ new_tags_set) - new_tags_set)
		if len(tags_added) - len(tags_to_remove) > PlaylistConfig.MAX_COMMON_TAGS :
			raise UserError('TOO_MANY_TAGS')
		all_video_ids, _ = listAllPlaylistVideosUnordered(pid)
		if tags_to_remove :
			tagdb.update_many_items_tags_pull(all_video_ids, tags_to_remove, makeUserMeta(user), session = s())
		if tags_added :
			tagdb.update_many_items_tags_merge(all_video_ids, tags_added, makeUserMeta(user), session = s())
		s.mark_succeed()

def listPlaylistsForVideo(vid) :
	video = tagdb.retrive_item({'_id': ObjectId(vid)})
	if video is None :
		raise UserError('VIDEO_NOT_EXIST')
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
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('removeVideoFromPlaylist', user, playlist)
		if playlist["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				raise UserError('VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST')
			db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gt': entry['rank']}}]}, {'$inc': {'rank': -1}}, session = s())
			db.playlist_items.delete_one({'_id': entry['_id']}, session = s())
			db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": -1}}, session = s())
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': makeUserMeta(user),
				'meta.modified_at': datetime.now()}}, session = s())
		else :
			raise UserError('EMPTY_PLAYLIST')
		video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
		if len(video_page) == 0 and page > 1 and video_count > 0 :
			# in case deleting video results in current page becomes empty, show the previous page
			video_page, video_count = listPlaylistVideos(pid, page - 2, page_size, user)
			s.mark_succeed()
			return {'videos': video_page, 'video_count': video_count, 'page': page - 1}
		s.mark_succeed()
		return {'videos': video_page, 'video_count': video_count, 'page': page}

def editPlaylist_MoveUp(pid, vid, page, page_size, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist_Reorder', user, playlist)
		if playlist["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				s.mark_failover()
				raise UserError('VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST')
			if entry['rank'] <= 0 :
				return None
			exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": entry['rank'] - 1}, session = s())
			db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': entry['rank'] - 1}}, session = s())
			db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': entry['rank']}}, session = s())
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': makeUserMeta(user),
				'meta.modified_at': datetime.now()}}, session = s())
			video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
			s.mark_succeed()
			return {'videos': video_page, 'video_count': video_count, 'page': page}
		else :
			raise UserError('EMPTY_PLAYLIST')

def editPlaylist_MoveDown(pid, vid, page, page_size, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist_Reorder', user, playlist)
		if playlist["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				raise UserError('VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST')
			if entry['rank'] >= playlist["videos"] - 1 :
				return None
			exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": entry['rank'] + 1}, session = s())
			db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': entry['rank'] + 1}}, session = s())
			db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': entry['rank']}}, session = s())
			db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
				'meta.modified_by': makeUserMeta(user),
				'meta.modified_at': datetime.now()}}, session = s())
			video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
			s.mark_succeed()
			return {'videos': video_page, 'video_count': video_count, 'page': page}
		else :
			raise UserError('EMPTY_PLAYLIST')

def insertIntoPlaylist(pid, vid, rank, user) :
	log(obj = {'pid': pid, 'vid': vid, 'rank': rank})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('insertIntoPlaylist', user, playlist)
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			raise UserError('VIDEO_NOT_EXIST')
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			raise UserError('VIDEO_LIMIT_EXCEEDED')
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			raise UserError('VIDEO_ALREADY_EXIST', vid)
		if rank < 0 :
			raise UserError('OUT_OF_RANGE')
		if rank > playlist['videos'] :
			rank = playlist['videos']
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gte': rank}}]}, {'$inc': {'rank': 1}}, session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": rank, "meta": makeUserMeta(user)}, session = s())
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()

def insertIntoPlaylistLockFree(pid, vid, rank, user) :
	log(obj = {'pid': pid, 'vid': vid, 'rank': rank})
	with MongoTransaction(client) as s :
		playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('insertIntoPlaylist', user, playlist)
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			raise UserError('VIDEO_NOT_EXIST')
		if playlist["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			raise UserError('VIDEO_LIMIT_EXCEEDED')
		if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
			raise UserError('VIDEO_ALREADY_EXIST', vid)
		if rank < 0 :
			raise UserError('OUT_OF_RANGE')
		if rank > playlist['videos'] :
			rank = playlist['videos']
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
		db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gte': rank}}]}, {'$inc': {'rank': 1}}, session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": rank, "meta": makeUserMeta(user)}, session = s())
		db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()}}, session = s())
		s.mark_succeed()

def createPlaylistFromCopies(pid, site, user) :
	if site not in ["youtube", "bilibili", "nicovideo", "twitter", "acfun"] :
		raise UserError("UNSUPPORTED_SITE")
	videos, _, playlist_obj = listAllPlaylistVideosOrdered(pid)
	new_pid = createPlaylist('english', playlist_obj['title']['english'] + ' - %s' % site, playlist_obj['desc']['english'], playlist_obj['cover'], user, playlist_obj['private'])
	with redis_lock.Lock(rdb, 'editLink'), redis_lock.Lock(rdb, "playlistEdit:" + str(new_pid)), MongoTransaction(client) as s :
		for video in videos :
			copies = video['item']['item']['copies']
			for cp in copies :
				item = tagdb.retrive_item(cp, s())
				if item['_id'] != video['vid'] and item['item']['site'] == site :
					addVideoToPlaylistLockFree(new_pid, item['_id'], user)
					break
		s.mark_succeed()
	return new_pid

