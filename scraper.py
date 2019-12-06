import os
import sys
import time
import asyncio
import traceback
import PIL

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

from spiders import dispatch
from db import tagdb, db, client

from bson import ObjectId

from services.playlist import addVideoToPlaylist, addVideoToPlaylistLockFree, insertIntoPlaylist, insertIntoPlaylistLockFree
from config import VideoConfig
from PIL import Image, ImageSequence

import io
import json

_COVER_PATH = os.getenv('IMAGE_PATH', "/images") + "/covers/"

def _gif_thumbnails(frames):
	for frame in frames:
		thumbnail = frame.copy()
		thumbnail.thumbnail((320, 200), Image.ANTIALIAS)
		yield thumbnail

# TODO: maybe make save image async?

async def _make_video_data(data, copies, playlists, url) :
	filename = ""
	for _ in range(3) :
		try :
			async with ClientSession() as session:
				async with session.get(data['thumbnailURL']) as resp:
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
							img.thumbnail((320, 200), Image.ANTIALIAS)
							img.save(_COVER_PATH + filename)
						break
		except Exception as ex :
			print(ex, file = sys.stderr)
			continue
	return {
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
		'rating': -1.0
	}

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
	tagdb.update_item_query(ObjectId(dst_vid), {"$set": {"item.copies": dst_copies}}, user, session = session)

class _PlaylistReorederHelper() :
	def __init__(self) :
		self.playlist_map = {}

	async def _add_to_playlist(self, dst_playlist) :
		if self.playlist_map[dst_playlist] :
			dst_rank = self.playlist_map[dst_playlist]['rank']
			playlist_ordered = self.playlist_map[dst_playlist]['all']
			cur_rank = 0
			try :
				async with RedisLockAsync(rdb, "playlistEdit:" + dst_playlist) :
					for unique_id in playlist_ordered :
						if unique_id in self.playlist_map[dst_playlist]['succeed'] :
							(video_id, _, user) = self.playlist_map[dst_playlist]['succeed'][unique_id]
							if dst_rank == -1 :
								addVideoToPlaylistLockFree(dst_playlist, video_id, user)
							else :
								insertIntoPlaylistLockFree(dst_playlist, video_id, dst_rank + cur_rank, user)
							cur_rank += 1
			except Exception as ex :
				print('****Exception _add_to_playlist! %s' % ex, file = sys.stderr)
				print(traceback.format_exc(), file = sys.stderr)
				for unique_id in playlist_ordered :
					if unique_id in self.playlist_map[dst_playlist]['succeed'] :
						(video_id, _, user) = self.playlist_map[dst_playlist]['succeed'][unique_id]
						if dst_rank == -1 :
							addVideoToPlaylistLockFree(dst_playlist, video_id, user)
						else :
							insertIntoPlaylistLockFree(dst_playlist, video_id, dst_rank + cur_rank, user)
						cur_rank += 1
			print('Total %d out of %d videos added to playlist %s' % (len(self.playlist_map[dst_playlist]['succeed']), len(self.playlist_map[dst_playlist]['all']), dst_playlist), file = sys.stderr)
			del self.playlist_map[dst_playlist]

	async def post_video_succeed(self, video_id, unique_id, dst_playlist, playlist_ordered, dst_rank, user) :
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
				await self._add_to_playlist(dst_playlist)

	async def post_video_failed(self, unique_id, dst_playlist, playlist_ordered, dst_rank) :
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
				await self._add_to_playlist(dst_playlist)

_playlist_reorder_helper = _PlaylistReorederHelper()

@usingResourceAsync('tags')
async def postVideoAsync(url, tags, dst_copy, dst_playlist, dst_rank, other_copies, playlist_ordered, user):
	parsed = None
	try :
		dst_playlist = str(dst_playlist)
		dst_rank = -1 if dst_rank is None else dst_rank
		tags = [tag.strip() for tag in tags]
		tags = tagdb.filter_tags(tags) # tags maybe removed while waiting in queue
		tags = tagdb.translate_tags(tags)
		tags = list(set(tags))
		parsed, unique_id = dispatch(url)
	except :
		pass
	if parsed is None :
		print('Parse failed for %s' % url, file = sys.stderr)
		await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank)
		return "PARSE_FAILED", {}
	print('Adding %s with copies %s and %s to playlist %s' % (url, dst_copy or '<None>', other_copies or '<None>', dst_playlist or '<None>'), file = sys.stderr)
	try :
		ret = await parsed.get_metadata_async(parsed, url)
		if ret["status"] == 'FAILED' :
			print('Fetch failed!!', file = sys.stderr)
			print(ret, file = sys.stderr)
			await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank)
			return "FETCH_FAILED", ret
		if hasattr(parsed, 'LOCAL_SPIDER') :
			url = ret["data"]["url"]
		else :
			url = clear_url(url)
		unique_id = ret["data"]["unique_id"]
		lock_id = "videoEdit:" + ret["data"]["unique_id"]
		async with RedisLockAsync(rdb, lock_id) :
			unique, conflicting_item = verifyUniqueness(ret["data"]["unique_id"])
			playlists = []
			#playlist_lock = None
			if dst_playlist :
				#playlist_lock = RedisLockAsync(rdb, "playlistEdit:" + str(dst_playlist))
				#playlist_lock.acquire()
				if db.playlists.find_one({'_id': ObjectId(dst_playlist)}) is not None :
					playlists = [ ObjectId(dst_playlist) ]
			if not unique:
				print('Video already exist as %s' % ret["data"]["unique_id"], file = sys.stderr)

				"""
				Update existing video
				"""
				
				"""
				if 'upload_time' not in conflicting_item['item'] or conflicting_item['item']['upload_time'] == '' or conflicting_item['item']['site'] == 'youtube':
					print('Updating time', file = sys.stderr)
					upload_time = ret['data']['uploadDate']
					with MongoTransaction(client) as s :
						tagdb.update_item_query(conflicting_item['_id'], {'$set': {'item.upload_time': upload_time}}, makeUserMeta(user), session = s())
						s.mark_succeed()
					if not tags :
						print('SUCCEED', file = sys.stderr)
						return 'SUCCEED', conflicting_item['_id']
				"""
				if conflicting_item['item']['site'] == 'nicovideo':
					print('Updating desc', file = sys.stderr)
					desc = ret['data']['desc']
					with MongoTransaction(client) as s :
						tagdb.update_item_query(conflicting_item['_id'], {'$set': {'item.desc': desc}}, makeUserMeta(user), session = s())
						s.mark_succeed()

				# this video already exist in the database
				# if the operation is to add a link to other copies and not adding self
				if (dst_copy and dst_copy != conflicting_item['_id']) or other_copies :
					print('Adding to to copies', file = sys.stderr)
					async with RedisLockAsync(rdb, 'editLink'), MongoTransaction(client) as s :
						print('Adding to to copies, lock acquired', file = sys.stderr)
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
								_addThiscopy(dst_vid, all_copies, makeUserMeta(user), session = s())
							print('Successfully added to copies', file = sys.stderr)
							s.mark_succeed()
						else :
							#if playlist_lock :
							#    playlist_lock.release()
							print('TOO_MANY_COPIES', file = sys.stderr)
							await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank)
							return "TOO_MANY_COPIES", {}
				# if the operation is adding this video to playlist
				if dst_playlist :
					print('Adding to playlist at position %d' % dst_rank, file = sys.stderr)
					if playlist_ordered :
						await _playlist_reorder_helper.post_video_succeed(conflicting_item['_id'], unique_id, dst_playlist, playlist_ordered, dst_rank, user)
					else :
						if dst_rank == -1 :
							addVideoToPlaylist(dst_playlist, conflicting_item['_id'], user)
						else :
							insertIntoPlaylist(dst_playlist, conflicting_item['_id'], dst_rank, user)
				# merge tags
				async with MongoTransaction(client) as s :
					print('Merging tags', file = sys.stderr)
					tagdb.update_item_tags_merge(conflicting_item['_id'], tags, makeUserMeta(user), session = s())
					s.mark_succeed()
				#if playlist_lock :
				#    playlist_lock.release()
				#return "VIDEO_ALREADY_EXIST", conflicting_item['_id']
				return "SUCCEED", conflicting_item['_id']
			else :
				# expand dst_copy to all copies linked to dst_copy
				if dst_copy or other_copies :
					print('Adding to to copies', file = sys.stderr)
					async with RedisLockAsync(rdb, 'editLink'), MongoTransaction(client) as s :
						print('Adding to to copies, lock acquired', file = sys.stderr)
						all_copies = _getAllCopies(dst_copy, session = s())
						# add videos from other copies
						for uid in other_copies :
							all_copies += _getAllCopies(uid, session = s(), use_unique_id = True)
						new_item_id = tagdb.add_item(tags, await _make_video_data(ret["data"], all_copies, playlists, url), makeUserMeta(user), session = s())
						all_copies.append(ObjectId(new_item_id))
						# remove duplicated items
						all_copies = list(set(all_copies))
						if len(all_copies) <= VideoConfig.MAX_COPIES :
							for dst_vid in all_copies :
								_addThiscopy(dst_vid, all_copies, makeUserMeta(user), session = s())
							print('Successfully added to copies', file = sys.stderr)
							s.mark_succeed()
						else :
							#if playlist_lock :
							#    playlist_lock.release()
							print('TOO_MANY_COPIES', file = sys.stderr)
							await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank)
							return "TOO_MANY_COPIES", {}
				else :
					async with MongoTransaction(client) as s :
						new_item_id = tagdb.add_item(tags, await _make_video_data(ret["data"], [], playlists, url), makeUserMeta(user), session = s())
						print('New video added to database', file = sys.stderr)
						s.mark_succeed()
				# if the operation is adding this video to playlist
				if dst_playlist :
					print('Adding to playlist at position %d' % dst_rank, file = sys.stderr)
					if playlist_ordered :
						await _playlist_reorder_helper.post_video_succeed(new_item_id, unique_id, dst_playlist, playlist_ordered, dst_rank, user)
					else :
						if dst_rank == -1 :
							addVideoToPlaylist(dst_playlist, new_item_id, user)
						else :
							insertIntoPlaylist(dst_playlist, new_item_id, dst_rank, user)
				#if playlist_lock :
				#    playlist_lock.release()
				print('SUCCEED', file = sys.stderr)
				return 'SUCCEED', new_item_id
	except UserError as ue :
		await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank)
		return ue.msg, {"aux": ue.aux, "traceback": traceback.format_exc()}
	except :
		await _playlist_reorder_helper.post_video_failed(unique_id, dst_playlist, playlist_ordered, dst_rank)
		print('****Exception!', file = sys.stderr)
		print(traceback.format_exc(), file = sys.stderr)
		try :
			problematic_lock = RedisLockAsync(rdb, 'editLink')
			problematic_lock.reset()
		except:
			pass
		return "UNKNOWN", traceback.format_exc()

async def postVideoAsyncJSON(param_json) :
	url = param_json['url']
	tags = param_json['tags']
	dst_copy = param_json['dst_copy']
	dst_playlist = param_json['dst_playlist']
	dst_rank = param_json['dst_rank']
	other_copies = param_json['other_copies']
	user = param_json['user']
	playlist_ordered = param_json['playlist_ordered']
	print(f'Posting {url}', file = sys.stderr)
	ret, ret_obj = await postVideoAsync(url, tags, dst_copy, dst_playlist, dst_rank, other_copies, playlist_ordered, user)
	print(f'Done posting {url}', file = sys.stderr)
	return {'result' : ret, 'result_obj' : ret_obj}

def verifyUniqueness(postingId):
	val = tagdb.retrive_item({"item.unique_id": postingId})
	return val is None, val

def verifyTags(tags):
	return tagdb.verify_tags([tag.strip() for tag in tags])

async def func_with_write_result(func, task_id, param_json) :
	ret = await func(param_json)
	ret_json = dumps({'finished' : True, 'key': task_id, 'data' : ret})
	rdb.set(f'task-{task_id}', ret_json, ex = 500)

async def task_runner(func, queue) :
	while True :
		task_param, task_id = await queue.get()
		task = asyncio.create_task(func_with_write_result(func, task_id, task_param))
		asyncio.gather(task)
		#await task
		queue.task_done()

async def put_task(queue, param_json) :
	task_id = random_bytes_str(16)
	ret_json = dumps({'finished' : False, 'key': task_id, 'data' : None})
	rdb.set(f'task-{task_id}', ret_json)
	await queue.put((param_json, task_id))
	return task_id

routes = web.RouteTableDef()
_async_queue = asyncio.Queue()

@routes.post("/")
async def post_video_async(request):
	rj = loads(await request.text())
	task_id = await put_task(_async_queue, rj)
	return web.json_response({'task_id' : task_id})

app = web.Application()
app.add_routes(routes)

async def start_async_app():
	# schedule task_runner to run
	task_runner_task = asyncio.create_task(task_runner(postVideoAsyncJSON, _async_queue))
	asyncio.gather(task_runner_task)

	# schedule web server to run
	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, '0.0.0.0', 5003)
	await site.start()
	print("Serving up app on 0.0.0.0:5003")
	return runner, site

loop = asyncio.get_event_loop()
runner, site = loop.run_until_complete(start_async_app())

try:
	loop.run_forever()
except KeyboardInterrupt as err:
	loop.run_until_complete(runner.cleanup())

