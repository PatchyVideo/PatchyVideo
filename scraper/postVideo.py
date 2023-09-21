
from .init import routes, init_funcs

import os
import sys
import time
import asyncio
import traceback
import PIL
import copy

from aiohttp import web
from aiohttp import ClientSession
from bson.json_util import dumps, loads
from init import rdb

from utils.jsontools import *
from utils.dbtools import makeUserMeta, MongoTransaction
from utils.crypto import random_bytes_str
from utils.http import clear_url
from utils.rwlock_async import modifyingResourceAsync, usingResourceAsync
from utils.lock_async import RedisLockAsync
from utils.exceptions import UserError

from .video import dispatch
from db import tagdb, db, client, playlist_db

from bson import ObjectId

from services.playlist import addVideoToPlaylist, addVideoToPlaylistLockFree, insertIntoPlaylist, insertIntoPlaylistLockFree
from services.tcb import filterOperation
from services.autotag import inferTagsFromVideo
from config import VideoConfig
from PIL import Image, ImageSequence
from utils.logger import log_e, setEventUserAndID, setEventOp
from config import PlaylistConfig
from datetime import datetime

import io
import json

_COVER_PATH = os.getenv('IMAGE_PATH', "/images") + "/covers/"

def _gif_thumbnails(frames):
	for frame in frames:
		thumbnail = frame.copy()
		thumbnail.thumbnail((320, 200), PIL.Image.Resampling.LANCZOS)
		yield thumbnail

# TODO: maybe make save image async?

def _cleanUtags(utags) :
	utags = [utag.replace(' ', '') for utag in utags]
	return list(set(utags))

_download_sem = asyncio.Semaphore(10)

async def notify_video_update(vid) :
	async with ClientSession() as session:
		async with session.post("http://patchyvideo-related-video-finder:5010/insert", json = {'vid': {'$oid': str(vid)}}) as resp:
			return

async def _download_thumbnail(url, user, event_id) :
	filename = ""
	if url :
		for attempt in range(3) :
			try :
				async with _download_sem :
					async with ClientSession() as session:
						async with session.get(url) as resp:
							if resp.status == 200 :
								img = Image.open(io.BytesIO(await resp.read()))
								if isinstance(img, PIL.GifImagePlugin.GifImageFile) :
									filename = random_bytes_str(24) + ".gif"
									frames = ImageSequence.Iterator(img)
									frames = _gif_thumbnails(frames)
									om = next(frames) # Handle first frame separately
									om.info = img.info # Copy sequence info
									om.save(_COVER_PATH + filename, save_all = True, append_images = list(frames), loop = 0)
								else :
									filename = random_bytes_str(24) + ".png"
									img.thumbnail((320, 200), PIL.Image.Resampling.LANCZOS)
									img.save(_COVER_PATH + filename)
								log_e(event_id, user, 'download_cover', obj = {'filename': filename})
								break
							else :
								log_e(event_id, user, 'download_cover', 'WARN', {'status_code': resp.status, 'attempt': attempt})
			except Exception as ex :
				import traceback
				traceback.print_exc()
				log_e(event_id, user, 'download_cover', 'WARN', {'ex': str(ex), 'attempt': attempt})
				continue
	return filename

async def _make_video_data(data, copies, playlists, url, user, event_id) :
	if 'cover_image_override' in data and data['cover_image_override'] :
		filename = data['cover_image_override']
	else :
		filename = await _download_thumbnail(data['thumbnailURL'], user, event_id)
	ret = {
		"url": (data['url_overwrite'] if 'url_overwrite' in data else url),
		"title": data['title'],
		"desc": data['desc'],
		"thumbnail_url": data['thumbnailURL'],
		"cover_image": filename,
		'site': data['site'],
		"unique_id": data['unique_id'],
		'series': playlists,
		'copies': copies,
		'upload_time': data['uploadDate'],
		'views': -1,
		'rating': -1.0,
		"utags": _cleanUtags(data['utags']) if 'utags' in data else [],
		"user_space_urls": data['user_space_urls'] if 'user_space_urls' in data else [],
		"placeholder": data["placeholder"] if 'placeholder' in data else False
	}
	if 'repost_type' in data :
		ret['repost_type'] = data['repost_type']
	else :
		ret['repost_type'] = 'unknown'
	if 'extra' in data :
		for k, v in data['extra'].items() :
			ret[k] = v
	return ret

async def _make_video_data_update(data, url, user, event_id, thumbnail_url = None) :
	if 'cover_image_override' in data and data['cover_image_override'] :
		filename = data['cover_image_override']
	else :
		filename = await _download_thumbnail(thumbnail_url, user, event_id)
	ret = {
		"url": (data['url_overwrite'] if 'url_overwrite' in data else url),
		"title": data['title'],
		"desc": data['desc'],
		"thumbnail_url": data['thumbnailURL'],
		'site': data['site'],
		"unique_id": data['unique_id'],
		'upload_time': data['uploadDate'],
		'views': -1,
		'rating': -1.0,
		"utags": _cleanUtags(data['utags']) if 'utags' in data else [],
		"user_space_urls": data['user_space_urls'] if 'user_space_urls' in data else [],
		"placeholder": data["placeholder"] if 'placeholder' in data else False
	}
	if 'repost_type' in data :
		ret['repost_type'] = data['repost_type']
	if 'extra' in data :
		for k, v in data['extra'].items() :
			ret[k] = v
	if filename :
		ret['cover_image'] = filename
	return ret

def _getAllCopies(vid, session, use_unique_id = False) :
	if not vid :
		return []
	if use_unique_id :
		this_video = tagdb.retrive_item({"item.unique_id": vid}, session = session)
	else :
		this_video = tagdb.retrive_item({"_id": ObjectId(vid)}, session = session)
	if this_video is None :
		return []
	copies = this_video['item']['copies']
	# add self
	copies.append(ObjectId(this_video['_id']))
	# use set to remove duplicated items
	return list(set(copies))

def _addThiscopy(dst_vid, this_vid, user, session):
	if this_vid is None :
		return
	dst_video = tagdb.retrive_item({"_id": ObjectId(dst_vid)}, session = session)
	if dst_video is None :
		return
	dst_copies = dst_video['item']['copies']
	if isinstance(this_vid, list) :
		dst_copies.extend(this_vid)
	else :
		dst_copies.append(ObjectId(this_vid))
	dst_copies = list(set(dst_copies) - set([ObjectId(dst_vid)]))
	tagdb.update_item_query(ObjectId(dst_vid), {"$set": {"item.copies": dst_copies}}, user = user, session = session)

class _PlaylistReorederHelper() :
	def __init__(self) :
		self.playlist_map = {}

	async def _add_to_playlist(self, dst_playlist, event_id, user_global) :
		if self.playlist_map[dst_playlist] :
			dst_rank = self.playlist_map[dst_playlist]['rank']
			playlist_ordered = self.playlist_map[dst_playlist]['all']
			try :
				# fast method
				async with RedisLockAsync(rdb, "playlistEdit:" + dst_playlist), MongoTransaction(client) as s :
					cur_rank = 0
					playlist = playlist_db.retrive_item(dst_playlist, session = s())
					if playlist is None :
						raise UserError('PLAYLIST_NOT_EXIST')
					if playlist["item"]["videos"] + len(self.playlist_map[dst_playlist]['succeed']) > PlaylistConfig.MAX_VIDEO_PER_PLAYLIST :
						raise UserError('VIDEO_LIMIT_EXCEEDED')
					playlist_videos = playlist["item"]['videos']
					for unique_id in playlist_ordered :
						if unique_id in self.playlist_map[dst_playlist]['succeed'] :
							(video_id, _, user) = self.playlist_map[dst_playlist]['succeed'][unique_id]
							if dst_rank == -1 :
								if filterOperation('editPlaylist', user, playlist, False) :
									if addVideoToPlaylistLockFree(dst_playlist, video_id, user, playlist_videos, session = s()) :
										playlist_videos += 1
							else :
								if filterOperation('editPlaylist', user, playlist, False) :
									if insertIntoPlaylistLockFree(dst_playlist, video_id, dst_rank + cur_rank, user, session = s()) :
										cur_rank += 1
					s.mark_succeed()
			except UserError as ue :
				# UserError, rereaise to upper level
				log_e(event_id, user_global, '_add_to_playlist', 'ERR', {'ex': str(ex), 'tb': traceback.format_exc()})
				del self.playlist_map[dst_playlist]
				rdb.set(f'playlist-batch-post-event-{dst_playlist}', b'done')
				raise ue
			except Exception as ex :
				# if anything goes wrong, fallback to slow method
				log_e(event_id, user_global, '_add_to_playlist', 'ERR', {'ex': str(ex), 'tb': traceback.format_exc()})
				cur_rank = 0
				for unique_id in playlist_ordered :
					if unique_id in self.playlist_map[dst_playlist]['succeed'] :
						(video_id, _, user) = self.playlist_map[dst_playlist]['succeed'][unique_id]
						# ignore error, add next video
						try :
							if dst_rank == -1 :
								addVideoToPlaylist(dst_playlist, video_id, user)
							else :
								insertIntoPlaylist(dst_playlist, video_id, dst_rank + cur_rank, user)
							cur_rank += 1
						except :
							pass
			log_e(event_id, user_global, '_add_to_playlist', 'MSG', {'succedd': len(self.playlist_map[dst_playlist]['succeed']), 'all': len(self.playlist_map[dst_playlist]['all']), 'pid': dst_playlist})
			del self.playlist_map[dst_playlist]
			rdb.set(f'playlist-batch-post-event-{dst_playlist}', b'done')

	async def post_video_succeed(self, video_id, unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id) :
		if video_id and unique_id and dst_playlist and playlist_ordered :
			if dst_playlist not in self.playlist_map :
				self.playlist_map[dst_playlist] = {}
				self.playlist_map[dst_playlist]['succeed'] = {}
				self.playlist_map[dst_playlist]['failed'] = {}
				self.playlist_map[dst_playlist]['rank'] = dst_rank
				self.playlist_map[dst_playlist]['all'] = playlist_ordered

			self.playlist_map[dst_playlist]['rank'] = min(dst_rank, self.playlist_map[dst_playlist]['rank'])
			self.playlist_map[dst_playlist]['succeed'][unique_id] = (video_id, unique_id, user)
			if unique_id in self.playlist_map[dst_playlist]['failed'] :
				del self.playlist_map[dst_playlist]['failed'][unique_id]

			if len(self.playlist_map[dst_playlist]['succeed']) + len(self.playlist_map[dst_playlist]['failed']) >= len(self.playlist_map[dst_playlist]['all']) :
				await self._add_to_playlist(dst_playlist, event_id, user)

	async def post_video_failed(self, unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id) :
		if unique_id and dst_playlist and playlist_ordered :
			if dst_playlist not in self.playlist_map :
				self.playlist_map[dst_playlist] = {}
				self.playlist_map[dst_playlist]['succeed'] = {}
				self.playlist_map[dst_playlist]['failed'] = {}
				self.playlist_map[dst_playlist]['rank'] = dst_rank
				self.playlist_map[dst_playlist]['all'] = playlist_ordered

			self.playlist_map[dst_playlist]['rank'] = min(dst_rank, self.playlist_map[dst_playlist]['rank'])
			self.playlist_map[dst_playlist]['failed'][unique_id] = unique_id
			if unique_id in self.playlist_map[dst_playlist]['succeed'] :
				del self.playlist_map[dst_playlist]['succeed'][unique_id]

			if len(self.playlist_map[dst_playlist]['succeed']) + len(self.playlist_map[dst_playlist]['failed']) >= len(self.playlist_map[dst_playlist]['all']) :
				await self._add_to_playlist(dst_playlist, event_id, user)

_playlist_reorder_helper = _PlaylistReorederHelper()

@usingResourceAsync('tags')
async def postVideoAsync(url, tags, dst_copy, dst_playlist, dst_rank, other_copies, repost_type, playlist_ordered, user, update_video_detail, event_id, field_override = None, use_autotag = False):
	parsed = None
	try :
		dst_playlist = str(dst_playlist)
		dst_rank = -1 if dst_rank is None else dst_rank
		#tags = tagdb.filter_and_translate_tags(tags)
		parsed, url = dispatch(url)
	except :
		pass
	if parsed is None :
		log_e(event_id, user, 'dispatcher', 'ERR', {'msg': 'PARSE_FAILED', 'url': url})
		await _playlist_reorder_helper.post_video_failed(url, dst_playlist, playlist_ordered, dst_rank, user, event_id)
		return "PARSE_FAILED", {}
	unique_id = await parsed.unique_id_async(self = parsed, link = url) # empty unique_id for b23.tv posts, fuck bilibli
	if not unique_id :
		ret = await parsed.get_metadata_async(parsed, url, update_video_detail)
		unique_id = ret['data']['unique_id']
	log_e(event_id, user, 'scraper', 'MSG', {'url': url, 'dst_copy': dst_copy, 'other_copies': other_copies, 'dst_playlist': dst_playlist})
	setEventOp('scraper')
	try :
		lock_id = "videoEdit:" + unique_id
		async with RedisLockAsync(rdb, lock_id) :
			unique, conflicting_item = verifyUniqueness(unique_id)
			if unique or update_video_detail :
				async with _download_sem :
					ret = await parsed.get_metadata_async(parsed, url, update_video_detail)
					print('-------------------', file = sys.stderr)
					print(ret, file = sys.stderr)
					print(ret['data'], file = sys.stderr)
					print('-------------------', file = sys.stderr)
					try :
						if repost_type :
							ret['data']['repost_type'] = repost_type
					except Exception :
						print('---------xxxxxxxxxx----------', file = sys.stderr)
						print(ret, file = sys.stderr)
						print(ret['data'], file = sys.stderr)
						print('----------xxxxxxxxxx---------', file = sys.stderr)
				if ret["status"] == 'FAILED' :
					log_e(event_id, user, 'downloader', 'WARN', {'msg': 'FETCH_FAILED', 'ret': ret})
					await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id)
					return "FETCH_FAILED", ret
				else :
					unique_id = ret['data']['unique_id']
			else :
				# build ret
				ret = makeResponseSuccess({
					'thumbnailURL': conflicting_item['item']['thumbnail_url'],
					'title' : conflicting_item['item']['title'],
					'desc' : conflicting_item['item']['desc'],
					'site': conflicting_item['item']['site'],
					'uploadDate' : conflicting_item['item']['upload_time'],
					"unique_id": conflicting_item['item']['unique_id'],
					"utags": conflicting_item['item']['utags']
				})
				for k, v in conflicting_item['item'].items() :
					ret['data'][k] = v
				if 'part_name' in conflicting_item['item'] :
					ret['part_name'] = conflicting_item['item']['part_name']
				if 'repost_type' in conflicting_item['item'] and conflicting_item['item']['repost_type'] :
					ret['data']['repost_type'] = repost_type
					tagdb.update_item_query(conflicting_item, {'$set': {'item.repost_type': repost_type}}, user = makeUserMeta(user))
			#if hasattr(parsed, 'LOCAL_CRAWLER') :
			#	url = ret["data"]["url"]
			#else :
			#	url = clear_url(url)
			
			use_override = False
			if field_override and '__condition' in field_override :
				condition = field_override['__condition']
				del field_override['__condition']
				if condition == 'any' :
					use_override = True
				elif condition == 'placeholder' and 'placeholder' in ret["data"] and ret["data"]['placeholder'] :
					use_override = True
			if use_override :
				for key in field_override :
					ret['data'][key] = field_override[key]
		
			
			playlists = []
			#playlist_lock = None
			if dst_playlist :
				#playlist_lock = RedisLockAsync(rdb, "playlistEdit:" + str(dst_playlist))
				#playlist_lock.acquire()
				if playlist_db.retrive_item(dst_playlist) is not None :
					playlists = [ ObjectId(dst_playlist) ]
			if not unique:
				log_e(event_id, user, 'scraper', level = 'MSG', obj = {'msg': 'ALREADY_EXIST', 'unique_id': ret["data"]["unique_id"]})

				"""
				Update existing video
				"""
				
				if update_video_detail :
					log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Updating video detail')
					with MongoTransaction(client) as s :
						old_item = tagdb.retrive_item(conflicting_item['_id'], session = s())['item']
						if old_item['thumbnail_url'] and old_item['cover_image'] :
							# old thumbnail exists, no need to download again
							new_detail = await _make_video_data_update(ret["data"], url, user, event_id)
						else :
							# old thumbnail does not exists, add to dict
							new_detail = await _make_video_data_update(ret["data"], url, user, event_id, ret["data"]["thumbnailURL"])
						for key in new_detail.keys() :
							old_item[key] = new_detail[key] # overwrite or add new field
						setEventUserAndID(user, event_id)
						tagdb.update_item_query(conflicting_item['_id'], {'$set': {'item': old_item}}, ['title', 'desc'], user = makeUserMeta(user), session = s())
						s.mark_succeed()
					return 'SUCCEED', conflicting_item['_id']

				# this video already exist in the database
				# if the operation is to add a link to other copies and not adding self
				if (dst_copy and dst_copy != conflicting_item['_id']) or other_copies :
					log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Adding to to copies')
					async with RedisLockAsync(rdb, 'editLink'), MongoTransaction(client) as s :
						log_e(event_id, user, level = 'MSG', obj = 'Adding to to copies, lock acquired')
						# find all copies of video dst_copy, self included
						all_copies = _getAllCopies(dst_copy, session = s())
						# find all videos linked to source video
						all_copies += _getAllCopies(conflicting_item['_id'], session = s())
						# add videos from other copies
						for uid in other_copies :
							all_copies += _getAllCopies(uid, session = s(), use_unique_id = True)
						# remove duplicated items
						all_copies = list(set(all_copies))
						# add this video to all other copies found
						if len(all_copies) <= VideoConfig.MAX_COPIES :
							for dst_vid in all_copies :
								setEventUserAndID(user, event_id)
								_addThiscopy(dst_vid, all_copies, makeUserMeta(user), session = s())
							log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Successfully added to copies')
							s.mark_succeed()
						else :
							#if playlist_lock :
							#    playlist_lock.release()
							log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Too many copies')
							await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id)
							return "TOO_MANY_COPIES", {}
				# if the operation is adding this video to playlist
				if dst_playlist :
					log_e(event_id, user, 'scraper', level = 'MSG', obj = {'msg': 'Adding to playlist at position', 'rank': dst_rank})
					if playlist_ordered :
						await _playlist_reorder_helper.post_video_succeed(conflicting_item['_id'], unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id)
					else :
						setEventUserAndID(user, event_id)
						if dst_rank == -1 :
							addVideoToPlaylist(dst_playlist, conflicting_item['_id'], user)
						else :
							insertIntoPlaylist(dst_playlist, conflicting_item['_id'], dst_rank, user)
				# merge tags
				async with MongoTransaction(client) as s :
					log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Merging tags')
					setEventUserAndID(user, event_id)
					tagdb.update_item_tags_merge(conflicting_item['_id'], tags, makeUserMeta(user), session = s(), remove_tagids = [354])
					s.mark_succeed()
				#if playlist_lock :
				#    playlist_lock.release()
				#return "VIDEO_ALREADY_EXIST", conflicting_item['_id']
				return "SUCCEED", conflicting_item['_id']
			else :
				# expand dst_copy to all copies linked to dst_copy
				if dst_copy or other_copies :
					log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Adding to to copies')
					async with RedisLockAsync(rdb, 'editLink'), MongoTransaction(client) as s :
						log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Adding to to copies, lock acquired')
						all_copies = _getAllCopies(dst_copy, session = s())
						# add videos from other copies
						for uid in other_copies :
							all_copies += _getAllCopies(uid, session = s(), use_unique_id = True)
						video_data = await _make_video_data(ret["data"], all_copies, playlists, url, user, event_id)
						setEventUserAndID(user, event_id)
						new_item_id = tagdb.add_item(tags, video_data, 3, ['title', 'desc'], makeUserMeta(user), session = s())
						all_copies.append(ObjectId(new_item_id))
						# remove duplicated items
						all_copies = list(set(all_copies))
						if len(all_copies) <= VideoConfig.MAX_COPIES :
							for dst_vid in all_copies :
								setEventUserAndID(user, event_id)
								_addThiscopy(dst_vid, all_copies, makeUserMeta(user), session = s())
							log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Successfully added to copies')
							s.mark_succeed()
						else :
							#if playlist_lock :
							#    playlist_lock.release()
							log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Too many copies')
							await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id)
							return "TOO_MANY_COPIES", {}
				else :
					async with MongoTransaction(client) as s :
						video_data = await _make_video_data(ret["data"], [], playlists, url, user, event_id)
						setEventUserAndID(user, event_id)
						if use_autotag :
							tags.extend(inferTagsFromVideo(video_data['utags'], video_data['title'], video_data['desc'], 'CHS', video_data['url'], video_data['user_space_urls']))
						new_item_id = tagdb.add_item(tags, video_data, 3, ['title', 'desc'], makeUserMeta(user), session = s())
						log_e(event_id, user, 'scraper', level = 'MSG', obj = {'msg': 'New video added to database', 'vid': new_item_id})
						s.mark_succeed()
				# if the operation is adding this video to playlist
				if dst_playlist :
					log_e(event_id, user, 'scraper', level = 'MSG', obj = {'msg': 'Adding to playlist at position', 'rank': dst_rank})
					if playlist_ordered :
						await _playlist_reorder_helper.post_video_succeed(new_item_id, unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id)
					else :
						setEventUserAndID(user, event_id)
						if dst_rank == -1 :
							addVideoToPlaylist(dst_playlist, new_item_id, user)
						else :
							insertIntoPlaylist(dst_playlist, new_item_id, dst_rank, user)
				#if playlist_lock :
				#    playlist_lock.release()
				log_e(event_id, user, 'scraper', level = 'MSG', obj = 'Done')
				return 'SUCCEED', new_item_id
	except UserError as ue :
		await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id)
		log_e(event_id, user, 'scraper', level = 'WARN', obj = {'ue': str(ue), 'tb': traceback.format_exc()})
		return ue.msg, {"aux": ue.aux, "traceback": traceback.format_exc()}
	except Exception as ex:
		await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank, user, event_id)
		log_e(event_id, user, 'scraper', level = 'ERR', obj = {'ex': str(ex), 'tb': traceback.format_exc()})
		try :
			problematic_lock = RedisLockAsync(rdb, 'editLink')
			problematic_lock.reset()
		except Exception :
			pass
		return "UNKNOWN", {"aux": "none", "traceback": traceback.format_exc()}#'\n'.join([repr(traceback.format_exc()), repr(traceback.extract_stack())])

async def postVideoAsyncJSON(param_json) :
	url = param_json['url']
	tags = param_json['tags']
	dst_copy = param_json['dst_copy']
	dst_playlist = param_json['dst_playlist']
	dst_rank = param_json['dst_rank']
	other_copies = param_json['other_copies']
	user = param_json['user']
	playlist_ordered = param_json['playlist_ordered']
	event_id = param_json['event_id']
	repost_type = param_json['repost_type']
	field_overrides = param_json['field_overrides'] if 'field_overrides' in param_json else None
	update_video_detail = param_json['update_video_detail'] if 'update_video_detail' in param_json else False
	use_autotag = param_json['use_autotag'] if 'use_autotag' in param_json else False
	ret, ret_obj = await postVideoAsync(url, tags, dst_copy, dst_playlist, dst_rank, other_copies, repost_type, playlist_ordered, user, update_video_detail, event_id, field_overrides, use_autotag)
	if not isinstance(ret_obj, dict) :
		try :
			await notify_video_update(ObjectId(ret_obj))
		except Exception as e :
			pass
	return {'result' : ret, 'result_obj' : ret_obj}

def verifyUniqueness(postingId):
	if not postingId :
		return True, None
	val = tagdb.retrive_item({"item.unique_id": postingId})
	return val is None, val

async def func_with_write_result(func, task_id, param_json) :
	ret = await func(param_json)
	key = 'posttasks-' + str(param_json['user']['_id'])
	rdb.lrem(key, 1, task_id)
	log_e(param_json['event_id'], param_json['user'], op = 'task_finished', obj = {'task_id': task_id})
	rdb.delete(f'task-{task_id}')
	if ret['result'] != 'SUCCEED' :
		param_json_for_user = copy.deepcopy(param_json)
		del param_json_for_user['user']
		del param_json_for_user['event_id']
		del param_json_for_user['playlist_ordered']
		if 'field_overrides' in param_json_for_user :
			del param_json_for_user['field_overrides']
		tagdb.db.failed_posts.insert_one({'uid': ObjectId(param_json['user']['_id']), 'ret': ret['result_obj'], 'post_param': param_json_for_user, 'time': datetime.now()})

async def task_runner(func, queue) :
	while True :
		task_param, task_id = await queue.get()
		task = asyncio.create_task(func_with_write_result(func, task_id, task_param))
		asyncio.gather(task)
		#await task
		queue.task_done()

async def put_task(queue, param_json) :
	task_id = random_bytes_str(16)
	param_json_for_user = copy.deepcopy(param_json)
	del param_json_for_user['user']
	del param_json_for_user['playlist_ordered']
	del param_json_for_user['event_id']
	if 'field_overrides' in param_json_for_user :
		del param_json_for_user['field_overrides']
	log_e(param_json['event_id'], param_json['user'], op = 'put_task', obj = {'task_id': task_id})
	ret_json = dumps({'finished' : False, 'key': task_id, 'data' : None, 'params': param_json_for_user})
	rdb.set(f'task-{task_id}', ret_json)
	key = 'posttasks-' + str(param_json['user']['_id'])
	rdb.lpush(key, task_id)
	await queue.put((param_json, task_id))
	return task_id

_async_queue = asyncio.Queue()

async def putVideoTask(video_json_obj) :
	return await put_task(_async_queue, video_json_obj)

@routes.post("/video")
async def post_video_async(request):
	rj = loads(await request.text())
	task_id = await put_task(_async_queue, rj)
	return web.json_response({'task_id' : task_id})

async def init() :
	# schedule task_runner to run
	task_runner_task = asyncio.create_task(task_runner(postVideoAsyncJSON, _async_queue))
	asyncio.gather(task_runner_task)

init_funcs.append(init)
