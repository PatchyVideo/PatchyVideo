
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, makeUserMetaObject, MongoTransaction
from utils.rwlock import usingResource, modifyingResource
from utils.exceptions import UserError

from db import tagdb, db, client, playlist_db

from datetime import datetime
from bson import ObjectId
from config import PlaylistConfig
from utils.logger import log
from services.tcb import filterSingleVideo, filterVideoList, filterOperation, isObjectAgnosticOperationPermitted

import redis_lock

from scraper.playlist import dispatch as dispatch_playlist
from utils.http import post_raw
from utils.logger import getEventID

import os

if os.getenv("FLASK_ENV", "development") == "production" :
	SCRAPER_ADDRESS = 'http://scraper:5003'
else :
	SCRAPER_ADDRESS = 'http://localhost:5003'

_LANG_MAP = {
	'CHS': {
		'creating': '创建中...'
	}
}

def _t(lang, tag, default) :
	if lang in _LANG_MAP and tag in _LANG_MAP[lang] :
		return _LANG_MAP[lang][tag]
	return default

def getPlaylist(pid, lang) :
	ret = playlist_db.retrive_item(pid)
	if not ret :
		raise UserError('PLAYLIST_NOT_EXIST')
	if 'tags' in ret :
		ret['tags_translated'], ret['tags_category'], ret['tags_tags'] = tagdb.translate_tag_ids_to_user_language(ret['tags'], lang)
	else :
		ret['tags_translated'], ret['tags_category'], ret['tags_tags'] = [], {}, {}
	return ret

def _is_authorised(pid_or_obj, user, op = 'edit') :
	if isinstance(pid_or_obj, str) :
		obj = playlist_db.retrive_item(pid_or_obj)
	else :
		obj = pid_or_obj
	creator = str(obj['meta']['created_by'])
	user_id = str(user['_id'])
	return creator == user_id or (op + 'Playlist' in user['access_control']['allowed_ops']) or user['access_control']['status'] == 'admin'

def isAuthorised(playlist, user) :
	return _is_authorised(playlist, user)

def createPlaylist(title, desc, cover, user, private = False) :
	log(obj = {'title': title, 'desc': desc, 'cover': cover, 'private': private})
	filterOperation('createPlaylist', user)
	if len(title) > PlaylistConfig.MAX_TITLE_LENGTH :
		raise UserError('TITLE_TOO_LONG')
	if len(desc) > PlaylistConfig.MAX_DESC_LENGTH :
		raise UserError('DESC_TOO_LONG')
	if len(cover) > PlaylistConfig.MAX_COVER_URL_LENGTH :
		raise UserError('URL_TOO_LONG')
	if not cover :
		cover = 'default-cover.jpg'
	if not title :
		raise UserError('EMPTY_TITLE')
	if not desc :
		raise UserError('EMPTY_DESC')
	pid = playlist_db.add_item(
		[],
		{
			"title": title,
			"desc": desc,
			"private": private,
			"views": int(0),
			"videos": int(0),
			"cover": cover
		},
		3,
		['title', 'desc'],
		makeUserMeta(user)
	)
	log(obj = {'pid': pid})
	return pid

def createPlaylistFromSingleVideo(vid, user) :
	log(obj = {'vid': vid})
	filterOperation('createPlaylist', user)
	video_obj = filterSingleVideo(vid, user)
	if video_obj is None :
		raise UserError('VIDEO_NOT_EXIST')
	new_playlist_id = createPlaylist(video_obj['item']['title'], video_obj['item']['desc'], video_obj['item']['cover_image'], user)
	log(obj = {'pid': new_playlist_id})
	addVideoToPlaylist(new_playlist_id, vid, user)
	return new_playlist_id

def _postPlaylistTask(url, pid, use_autotag, user, extend = False) :
	post_obj = {'use_autotag': use_autotag, 'url': url, 'pid': pid, 'user': user, 'event_id': getEventID(), 'extend': extend}
	post_obj_json_str = dumps(post_obj)
	ret_obj = loads(post_raw(SCRAPER_ADDRESS + "/playlist", post_obj_json_str.encode('utf-8')).text)
	return ret_obj['task_id']

def createPlaylistFromExistingPlaylist(url, user, user_language, use_autotag = False) :
	log(obj = {'url': url})
	filterOperation('createPlaylist', user)
	cralwer, cleanURL = dispatch_playlist(url)
	if not cralwer :
		raise UserError('UNSUPPORTED_PLAYLIST_URL')
	prompt = _t(user_language, 'creating', 'Creating, please wait...')
	new_playlist_id = createPlaylist(prompt, str(datetime.now()), '', user)
	log(obj = {'pid': new_playlist_id})
	task_id = _postPlaylistTask(cleanURL, new_playlist_id, use_autotag, user)
	return new_playlist_id, task_id

def extendPlaylistFromExistingPlaylist(pid, url, user, use_autotag = False) :
	log(obj = {'url': url, 'pid': pid})
	filterOperation('editPlaylist', user)
	if not playlist_db.retrive_item(pid) :
		raise UserError('PLAYLIST_NOT_EXIST')
	cralwer, cleanURL = dispatch_playlist(url)
	if not cralwer :
		raise UserError('UNSUPPORTED_PLAYLIST_URL')
	task_id = _postPlaylistTask(cleanURL, pid, use_autotag, user, extend = True)
	return task_id

def removePlaylist(pid, user) :
	log(obj = {'pid': pid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = playlist_db.retrive_item(pid)
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('removePlaylist', user, list_obj)
		all_items = db.playlist_items.find({"pid": ObjectId(pid)}, session = s())
		log(obj = {'items': [i for i in all_items]})
		db.playlist_items.delete_many({"pid": ObjectId(pid)}, session = s())
		playlist_db.remove_item(pid, user, session = s())
		from services.playlistFolder import deletePlaylist
		deletePlaylist(pid, session = s())
		s.mark_succeed()

def listMyPlaylists(user, page_idx = 0, page_size = 10000, query_obj = {}, order = 'last_modified') :
	if order not in ['latest', 'oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	result = playlist_db.retrive_items({'$and': [{'meta.created_by': ObjectId(user['_id'])}, query_obj]})
	if order == 'last_modified' :
		result = result.sort([("meta.modified_at", -1)])
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	result = result.skip(page_idx * page_size).limit(page_size)
	return result, result.count()

def listMyPlaylistsAgainstSingleVideo(user, vid, page_idx = 0, page_size = 10000, query_obj = {}, order = 'last_modified') :
	if order not in ['latest', 'oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	result = playlist_db.retrive_items({'$and': [{'meta.created_by': ObjectId(user['_id'])}, query_obj]})
	if order == 'last_modified' :
		result = result.sort([("meta.modified_at", -1)])
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	result = result.skip(page_idx * page_size).limit(page_size)
	count = result.count()
	result = [i for i in result]
	result_dict = {str(x['_id']): x for x in result}
	pids = [i['_id'] for i in result]
	video_items = db.playlist_items.find({'pid': {'$in': pids}, 'vid': ObjectId(vid)})
	for item in video_items :
		result_dict[str(item['pid'])]['exist'] = True
	return result_dict.values(), count

def listYourPlaylists(user, uid, page_idx = 0, page_size = 10000, query_obj = {}, order = 'last_modified') :
	if order not in ['latest', 'oldest', 'last_modified'] :
		raise UserError('INCORRECT_ORDER')
	if isObjectAgnosticOperationPermitted('viewPrivatePlaylist', user) :
		auth_obj = {}
	else :
		auth_obj = {'item.private': False}
	result = playlist_db.retrive_items({'$and': [{'meta.created_by': ObjectId(uid)}, auth_obj, query_obj]})
	if order == 'last_modified' :
		result = result.sort([("meta.modified_at", -1)])
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	result = result.skip(page_idx * page_size).limit(page_size)
	return result, result.count()

def updatePlaylistCover(pid, cover, user) :
	log(obj = {'pid': pid, 'cover': cover})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = playlist_db.retrive_item(pid)
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, list_obj)
		playlist_db.update_item_query(list_obj, {'$set': {"item.cover": cover}}, session = s())
		s.mark_succeed()

def updatePlaylistCoverVID(pid, vid, page, page_size, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = playlist_db.retrive_item(pid)
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, list_obj)
		video_obj = filterSingleVideo(vid, user)
		if video_obj is None :
			raise UserError('VIDEO_NOT_EXIST')
		cover = video_obj['item']['cover_image']
		playlist_db.update_item_query(list_obj, {'$set': {"item.cover": cover}}, session = s())
		#video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
		s.mark_succeed()
		#return {'videos': video_page, 'video_count': video_count, 'page': page}

def updatePlaylistInfo(pid, title, desc, cover, user, private = False) :
	log(obj = {'title': title, 'desc': desc, 'cover': cover, 'private': private})
	if len(title) > PlaylistConfig.MAX_TITLE_LENGTH :
		raise UserError('TITLE_TOO_LONG')
	if len(desc) > PlaylistConfig.MAX_DESC_LENGTH :
		raise UserError('DESC_TOO_LONG')
	if cover and len(cover) > PlaylistConfig.MAX_COVER_URL_LENGTH :
		raise UserError('URL_TOO_LONG')
	if not title :
		raise UserError('EMPTY_TITLE')
	if not desc :
		raise UserError('EMPTY_DESC')
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = playlist_db.retrive_item(pid)
		log(obj = {'playlist': list_obj})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, list_obj)
		if cover :
			playlist_db.update_item_query(list_obj, {'$set': {"item.cover": cover}}, session = s())
		playlist_db.update_item_query(list_obj, {'$set': {"item.title": title, "item.desc": desc, "item.private": private}}, session = s())
		s.mark_succeed()

def updatePlaylistTags(pid, new_tags, user) :
	log(obj = {'pid': pid, 'new_tags': new_tags})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		list_obj = playlist_db.retrive_item(pid)
		log(obj = {'playlist': list_obj, 'old_tags': list_obj['tags'] if 'tags' in list_obj else []})
		if list_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, list_obj)
		playlist_db.update_item_tags(list_obj, new_tags, user, session = s())
		s.mark_succeed()

def addVideoToPlaylist(pid, vid, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = playlist_db.retrive_item(pid)
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist)
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			raise UserError('VIDEO_NOT_EXIST')
		if playlist['item']["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			raise UserError('VIDEO_LIMIT_EXCEEDED')
		conflicting_item = db.playlist_items.find_one({'pid': ObjectId(pid), 'vid': ObjectId(vid)}, session = s())
		if conflicting_item is not None :
			editPlaylist_MoveLockFree(pid, conflicting_item, int(playlist['item']["videos"]), session = s())
			playlist_db.update_item_query(playlist, {}, session = s())
			s.mark_succeed()
			return
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": int(playlist['item']["videos"]), "meta": makeUserMeta(user)}, session = s())
		playlist_db.update_item_query(playlist, {"$inc": {"item.videos": int(1)}}, session = s())
		s.mark_succeed()

def addVideoToPlaylistLockFree(pid, vid, user, rank, session) :
	log(obj = {'pid': pid, 'vid': vid})
	if tagdb.retrive_item({'_id': ObjectId(vid)}, session = session) is None :
		#raise UserError('VIDEO_NOT_EXIST')
		return False
	conflicting_item = db.playlist_items.find_one({'pid': ObjectId(pid), 'vid': ObjectId(vid)}, session = session)
	if conflicting_item is not None :
		editPlaylist_MoveLockFree(pid, conflicting_item, rank, session = session)
		playlist_db.update_item_query(pid, {}, session = session)
		return False
	playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = session)['item']['series']
	playlists.append(ObjectId(pid))
	playlists = list(set(playlists))
	tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = session)
	db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": int(rank), "meta": makeUserMeta(user)}, session = session)
	playlist_db.update_item_query(pid, {"$inc": {"item.videos": int(1)}}, session = session)
	return True

def listPlaylistVideosWithAuthorizationInfo(pid, page_idx, page_size, user) :
	playlist = playlist_db.retrive_item(pid)
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
	if playlist['item']['private'] :
		filterOperation('viewPrivatePlaylist', user, playlist)
	ans_obj = db.playlist_items.aggregate([
		{
			'$match': {
				"pid": ObjectId(pid)
			}
		},
		{
			'$lookup': {
				'from': 'videos',
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
	return ret, playlist['item']['videos'], _is_authorised(playlist, user)

def listPlaylistVideos(pid, page_idx, page_size, user) :
	playlist = playlist_db.retrive_item(pid)
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
	if playlist['item']['private'] :
		filterOperation('viewPrivatePlaylist', user, playlist)
	ans_obj = db.playlist_items.aggregate([
		{
			'$match': {
				"pid": ObjectId(pid)
			}
		},
		{
			'$lookup': {
				'from': 'videos',
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
	return ret, playlist['item']['videos']

def listAllPlaylistVideosUnordered(pid) :
	playlist = playlist_db.retrive_item(pid)
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
	ans_obj = db.playlist_items.find({"pid": ObjectId(pid)})
	return [ObjectId(item['vid']) for item in ans_obj], playlist['item']['videos']

def listAllPlaylistVideosOrdered(pid, user) :
	playlist = playlist_db.retrive_item(pid)
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
	if playlist['item']['private'] :
		filterOperation('viewPrivatePlaylist', user, playlist)
	ans_obj = db.playlist_items.aggregate([
		{
			'$match': {
				"pid": ObjectId(pid)
			}
		},
		{
			'$lookup': {
				'from': 'videos',
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
	return [i for i in ans_obj], playlist['item']['videos'], playlist

def listPlaylists(user, page_idx, page_size, query_str = '', order = 'latest', qtype = 'tag', additional_constraint = '') :
	sort_obj = { "meta.created_at" : 1 }
	if order == 'latest':
		sort_obj = { "meta.created_at" : -1 }
	if order == 'last_modified':
		sort_obj = { "meta.modified_at" : -1 }
	if order == 'oldest':
		sort_obj = { "meta.created_at" : 1 }
	if order == 'views':
		sort_obj = { "item.views" : 1 }
	if isObjectAgnosticOperationPermitted('viewPrivatePlaylist', user) :
		auth_obj = {}
	else :
		auth_obj = {'$or': [{'meta.created_by': user['_id'] if user else ''}, {'item.private': False, 'item.videos': {'$gt': 1}}]}
	query_obj, tags = tagdb.compile_query(query_str, qtype)
	query_obj_extra, _ = tagdb.compile_query(additional_constraint, 'tag')
	query = {'$and': [query_obj, query_obj_extra, auth_obj]}
	ans_obj = playlist_db.aggregate([
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
			"user_detail.meta": 0,
			"user_detail.profile.email": 0,
			"user_detail.settings": 0
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

def listCommonTagIDs(pid, user) :
	playlist = playlist_db.retrive_item(pid)
	if playlist is None :
		raise UserError('PLAYLIST_NOT_EXIST')
	if playlist['item']['private'] :
		filterOperation('viewPrivatePlaylist', user, playlist)
	result = db.playlist_items.aggregate([
	{
		"$match" : {
			"pid" : ObjectId(pid)
		}
	},
	{
		"$lookup" : {
			"from" : 'videos',
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
			"tags" : {'$filter': {'input': '$video.tags', 'as': 'tag', 'cond': {'$lt': ['$$tag', 0x80000000]}}}
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
def listCommonTags(user, pid, language) :
	return tagdb.translate_tag_ids_to_user_language(listCommonTagIDs(pid, user), language)[0]

@usingResource('tags')
def updateCommonTags(pid, tags, user) :
	log(obj = {'pid': pid, 'tags': tags})
	with MongoTransaction(client) as s :
		playlist_obj = playlist_db.retrive_item(pid)
		if playlist_obj is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist_obj)
		# user is editing video tags, not the playlist itself, no need to lock playlist
		tags = tagdb.filter_and_translate_tags(tags, session = s())
		old_tags = listCommonTagIDs(pid, user)
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

def listPlaylistsForVideo(user, vid) :
	video = tagdb.retrive_item({'_id': ObjectId(vid)})
	if video is None :
		raise UserError('VIDEO_NOT_EXIST')
	if isObjectAgnosticOperationPermitted('viewPrivatePlaylist', user) :
		auth_obj = {}
	else :
		auth_obj = {'$or': [{'playlist.meta.created_by': user['_id'] if user else ''}, {'playlist.item.private': False, 'playlist.item.videos': {'$gt': 1}}]}
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
				}
				]
			}
		},
		{
			'$lookup': {
				'from': 'playlist_metas',
				'localField': 'pid',
				'foreignField': '_id',
				'as': 'playlist'
			}
		},
		{
			'$unwind': {
				'path': '$playlist'
			}
		},
		{
			'$match': auth_obj
		}
	])
	ans = []
	for obj in result :
		playlist_obj = obj['playlist']
		playlist_obj['prev'] = ''
		playlist_obj['next'] = ''
		rank = obj['rank']
		if rank > 0 :
			playlist_obj['prev'] = str(db.playlist_items.find_one({'pid': playlist_obj['_id'], 'rank': int(rank - 1)})['vid'])
		if rank + 1 < playlist_obj['item']['videos'] :
			playlist_obj['next'] = str(db.playlist_items.find_one({'pid': playlist_obj['_id'], 'rank': int(rank + 1)})['vid'])
		ans.append(playlist_obj)
	return ans

def listPlaylistsForVideoNoAuth(vid) :
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
				}
				]
			}
		},
		{
			'$lookup': {
				'from': 'playlist_metas',
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
			playlist_obj['prev'] = str(db.playlist_items.find_one({'pid': playlist_obj['_id'], 'rank': int(rank - 1)})['vid'])
		if rank + 1 < playlist_obj['item']['videos'] :
			playlist_obj['next'] = str(db.playlist_items.find_one({'pid': playlist_obj['_id'], 'rank': int(rank + 1)})['vid'])
		ans.append(playlist_obj)
	return ans

def removeVideoFromPlaylist(pid, vid, page, page_size, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = playlist_db.retrive_item(pid, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist)
		if playlist['item']["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				raise UserError('VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST')
			db.playlist_items.update_many({'pid': ObjectId(pid), 'rank': {'$gt': entry['rank']}}, {'$inc': {'rank': int(-1)}}, session = s())
			db.playlist_items.delete_one({'_id': entry['_id']}, session = s())
			playlist_db.update_item_query(playlist, {"$inc": {"item.videos": int(-1)}}, session = s())
		else :
			raise UserError('EMPTY_PLAYLIST')
		"""
		video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
		if len(video_page) == 0 and page > 1 and video_count > 0 :
			# in case deleting video results in current page becomes empty, show the previous page
			video_page, video_count = listPlaylistVideos(pid, page - 2, page_size, user)
			s.mark_succeed()
			return {'videos': video_page, 'video_count': video_count, 'page': page - 1}
		"""
		s.mark_succeed()
		#return {'videos': video_page, 'video_count': video_count, 'page': page}

def editPlaylist_MoveUp(pid, vid, page, page_size, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = playlist_db.retrive_item(pid, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist)
		if playlist['item']["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				s.mark_failover()
				raise UserError('VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST')
			if entry['rank'] <= 0 :
				return None
			exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": int(entry['rank'] - 1)}, session = s())
			db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': int(entry['rank'] - 1)}}, session = s())
			db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': int(entry['rank'])}}, session = s())
			playlist_db.update_item_query(playlist, {}, session = s())
			#video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
			s.mark_succeed()
			#return {'videos': video_page, 'video_count': video_count, 'page': page}
		else :
			raise UserError('EMPTY_PLAYLIST')

def editPlaylist_MoveDown(pid, vid, page, page_size, user) :
	log(obj = {'pid': pid, 'vid': vid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = playlist_db.retrive_item(pid, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist)
		if playlist['item']["videos"] > 0 :
			entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
			if entry is None :
				raise UserError('VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST')
			if entry['rank'] >= playlist['item']["videos"] - 1 :
				return None
			exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": int(entry['rank'] + 1)}, session = s())
			db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': int(entry['rank'] + 1)}}, session = s())
			db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': int(entry['rank'])}}, session = s())
			playlist_db.update_item_query(playlist, {}, session = s())
			#video_page, video_count = listPlaylistVideos(pid, page - 1, page_size, user)
			s.mark_succeed()
			#return {'videos': video_page, 'video_count': video_count, 'page': page}
		else :
			raise UserError('EMPTY_PLAYLIST')

def editPlaylist_Move(pid, vid, to_rank, user) :
	log(obj = {'pid': pid, 'vid': vid, 'to_rank': to_rank})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = playlist_db.retrive_item(pid, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist)
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			raise UserError('VIDEO_NOT_EXIST')
		if to_rank < 0 :
			raise UserError('OUT_OF_RANGE')
		if to_rank > playlist['item']['videos'] :
			to_rank = int(playlist['item']['videos'])
		editPlaylist_MoveLockFree(pid, vid, to_rank, session = s())
		playlist_db.update_item_query(playlist, {}, session = s())
		s.mark_succeed()

def editPlaylist_MoveLockFree(pid, vid_or_playlist_item, to_rank, session) :
	log(obj = {'pid': pid, 'vid': vid_or_playlist_item, 'to_rank': to_rank})
	if isinstance(vid_or_playlist_item, str) or isinstance(vid_or_playlist_item, ObjectId) :
		playlist_item = db.playlist_items.find_one({'pid': ObjectId(pid), 'vid': ObjectId(vid_or_playlist_item)}, session = session)
	else :
		playlist_item = vid_or_playlist_item
	from_rank = int(playlist_item['rank'])
	if from_rank == to_rank or from_rank + 1 == to_rank :
		return False
	if to_rank > from_rank :
		db.playlist_items.update_many({'pid': ObjectId(pid), 'rank': {'$gt': from_rank, '$lt': to_rank}}, {'$inc': {'rank': int(-1)}}, session = session)
		db.playlist_items.update_one({'_id': playlist_item['_id']}, {'$set': {'rank': int(to_rank - 1)}}, session = session)
	else :
		db.playlist_items.update_many({'pid': ObjectId(pid), 'rank': {'$gte': to_rank, '$lt': from_rank}}, {'$inc': {'rank': int(1)}}, session = session)
		db.playlist_items.update_one({'_id': playlist_item['_id']}, {'$set': {'rank': int(to_rank)}}, session = session)
	return True

def insertIntoPlaylist(pid, vid, rank, user) :
	log(obj = {'pid': pid, 'vid': vid, 'rank': rank})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = playlist_db.retrive_item(pid, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist)
		if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
			raise UserError('VIDEO_NOT_EXIST')
		if playlist['item']["videos"] > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
			raise UserError('VIDEO_LIMIT_EXCEEDED')
		conflicting_item = db.playlist_items.find_one({'pid': ObjectId(pid), 'vid': ObjectId(vid)}, session = s())
		if conflicting_item is not None :
			editPlaylist_MoveLockFree(pid, conflicting_item, rank, session = s())
			playlist_db.update_item_query(playlist, {}, session = s())
			s.mark_succeed()
			return
		if rank < 0 :
			raise UserError('OUT_OF_RANGE')
		if rank > playlist['item']['videos'] :
			rank = int(playlist['item']['videos'])
		playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
		playlists.append(ObjectId(pid))
		playlists = list(set(playlists))
		tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = s())
		playlist_db.update_item_query(playlist, {"$inc": {"item.videos": int(1)}}, session = s())
		db.playlist_items.update_many({'pid': ObjectId(pid), 'rank': {'$gte': rank}}, {'$inc': {'rank': int(1)}}, session = s())
		db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": int(rank), "meta": makeUserMeta(user)}, session = s())
		s.mark_succeed()

def insertIntoPlaylistLockFree(pid, vid, rank, user, session) :
	log(obj = {'pid': pid, 'vid': vid, 'rank': rank})
	if tagdb.retrive_item({'_id': ObjectId(vid)}, session = session) is None :
		#raise UserError('VIDEO_NOT_EXIST')
		return False
	conflicting_item = db.playlist_items.find_one({'pid': ObjectId(pid), 'vid': ObjectId(vid)}, session = session)
	if conflicting_item is not None :
		editPlaylist_MoveLockFree(pid, conflicting_item, rank, session = session)
		playlist_db.update_item_query(pid, {}, session = s())
		if conflicting_item['rank'] >= rank :
			return True
		else :
			return False
	playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = session)['item']['series']
	playlists.append(ObjectId(pid))
	playlists = list(set(playlists))
	tagdb.update_item_query(ObjectId(vid), {'$set': {'item.series': playlists}}, makeUserMeta(user), session = session)
	playlist_db.update_item_query(pid, {"$inc": {"item.videos": int(1)}}, session = session)
	db.playlist_items.update_many({'pid': ObjectId(pid), 'rank': {'$gte': rank}}, {'$inc': {'rank': int(1)}}, session = session)
	db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": int(rank), "meta": makeUserMeta(user)}, session = session)
	return True

def inversePlaylistOrder(pid, user) :
	log(obj = {'pid': pid})
	with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
		playlist = playlist_db.retrive_item(pid, session = s())
		if playlist is None :
			raise UserError('PLAYLIST_NOT_EXIST')
		filterOperation('editPlaylist', user, playlist)
		db.playlist_items.update_many({"pid": playlist["_id"]}, {'$bit': {'rank': {'xor': int(-1)}}})
		db.playlist_items.update_many({"pid": playlist["_id"]}, {'$inc': {'rank': int(playlist['item']['videos'])}})
		s.mark_succeed()

def createPlaylistFromCopies(pid, site, user) :
	if site not in ["youtube", "bilibili", "nicovideo", "twitter", "acfun"] :
		raise UserError("UNSUPPORTED_SITE")
	videos, _, playlist_obj = listAllPlaylistVideosOrdered(pid, user)
	new_pid = createPlaylist(playlist_obj['item']['title'] + ' - %s' % site, playlist_obj['item']['desc'], playlist_obj['item']['cover'], user, playlist_obj['item']['private'])
	with redis_lock.Lock(rdb, 'editLink'), redis_lock.Lock(rdb, "playlistEdit:" + str(new_pid)), MongoTransaction(client) as s :
		rank = 0
		for video in videos :
			copies = video['item']['item']['copies']
			for cp in copies :
				item = tagdb.retrive_item(cp, session = s())
				if item['_id'] != video['vid'] and item['item']['site'] == site :
					addVideoToPlaylistLockFree(new_pid, item['_id'], user, rank, session = s())
					rank += 1
					break
		s.mark_succeed()
	return new_pid

