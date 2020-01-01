
from .init import routes, init_funcs

import traceback
import copy
import asyncio

from aiohttp import web
from aiohttp import ClientSession
from bson.json_util import loads, dumps
from bson import ObjectId

from init import rdb
from db import tagdb
from services.playlist import updatePlaylistInfo

from utils.logger import log_e
from utils.crypto import random_bytes_str
from utils.exceptions import UserError
from utils.http import post_raw

from .playlist import dispatch
from .video import dispatch as dispatch_video
from .postVideo import putVideoTask

async def postTask(json_obj) :
	return await putVideoTask(json_obj)

def _createJsonForPosting(url, dst_playlist, playlist_ordered, use_autotag, user, event_id) :
	return {
		'url' : url,
		'tags' : [],
		'dst_copy' : '',
		'dst_playlist' : dst_playlist,
		'dst_rank' : -1,
		'other_copies' : [],
		'user' : user,
		'playlist_ordered' : playlist_ordered,
		'event_id': event_id
	}

async def _postVideosBatch(videos, pid, use_autotag, user, event_id) :
	unique_ids = []
	unique_id_urls = []
	for url in videos :
		obj, cleanURL = dispatch_video(url)
		# Here we allow batch post to be partially successful
		if obj is not None :
			uid = obj.unique_id(obj, cleanURL)
			if not uid in unique_ids : # remove duplicated items
				unique_ids.append(uid)
				unique_id_urls.append((uid, url))
	task_ids = []
	for _, cleanURL in unique_id_urls :
		task_id = await postTask(_createJsonForPosting(cleanURL, pid, unique_ids, use_autotag, user, event_id))
		task_ids.append(task_id)
	return task_ids
	
async def postPlaylistAsync(url, pid, use_autotag, user, event_id) :
	crawler, _ = dispatch(url)
	website_pid = crawler.get_pid(self = crawler, url = url)
	log_e(event_id, user, 'postPlaylistAsync', obj = {'website_pid': website_pid, 'pid': pid})
	videos = []
	async for single_video_url in crawler.run(self = crawler, website_pid = website_pid) :
		videos.append(single_video_url)
	log_e(event_id, user, 'postPlaylistAsync', obj = {'video_count': len(videos)})
	if len(videos) == 0 :
		raise UserError('EMPTY_PLAYLIST')
	metadata = await crawler.get_metadata(self = crawler, url = url)
	updatePlaylistInfo(pid, "english", metadata['title'], metadata['desc'], '', user)
	task_ids = await _postVideosBatch(videos, pid, use_autotag, user, event_id)
	return 'SUCCEED', {'task_ids': task_ids}

async def postPlaylistAsyncNoexcept(url, pid, use_autotag, user, event_id) :
	try :
		return await postPlaylistAsync(url, pid, use_autotag, user, event_id)
	except UserError as ue :
		log_e(event_id, user, 'scraper', level = 'WARN', obj = {'ue': str(ue)})
		return ue.msg, {"aux": ue.aux, "traceback": traceback.format_exc()}
	except Exception as ex :
		log_e(event_id, user, 'scraper', level = 'ERR', obj = {'ex': str(ex)})
		return "UNKNOWN", traceback.format_exc()

async def postPlaylistAsyncJSON(param_json) :
	use_autotag = param_json['use_autotag']
	url = param_json['url']
	pid = param_json['pid']
	user = param_json['user']
	event_id = param_json['event_id']
	ret, ret_obj = await postPlaylistAsyncNoexcept(url, pid, use_autotag, user, event_id)
	return {'result' : ret, 'result_obj' : ret_obj}

async def func_with_write_result(func, task_id, param_json) :
	ret = await func(param_json)
	key = 'post-playlist-tasks-' + str(param_json['user']['_id'])
	rdb.lrem(key, 1, task_id)
	log_e(param_json['event_id'], param_json['user'], op = 'task_finished', obj = {'task_id': task_id})
	rdb.delete(f'task-playlist-{task_id}')
	if ret['result'] != 'SUCCEED' :
		param_json_for_user = copy.deepcopy(param_json)
		del param_json_for_user['user']
		del param_json_for_user['event_id']
		tagdb.db.failed_playlist_posts.insert_one({'uid': ObjectId(param_json['user']['_id']), 'ret': ret, 'post_param': param_json_for_user})

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
	del param_json_for_user['event_id']
	log_e(param_json['event_id'], param_json['user'], op = 'put_task', obj = {'task_id': task_id})
	ret_json = dumps({'finished' : False, 'key': task_id, 'data' : None, 'params': param_json_for_user})
	rdb.set(f'task-playlist-{task_id}', ret_json)
	key = 'post-playlist-tasks-' + str(param_json['user']['_id'])
	rdb.lpush(key, task_id)
	await queue.put((param_json, task_id))
	return task_id

_async_queue = asyncio.Queue()

@routes.post("/playlist")
async def post_playlist_async(request):
	rj = loads(await request.text())
	task_id = await put_task(_async_queue, rj)
	return web.json_response({'task_id' : task_id})

async def init() :
	# schedule task_runner to run
	task_runner_task = asyncio.create_task(task_runner(postPlaylistAsyncJSON, _async_queue))
	asyncio.gather(task_runner_task)

init_funcs.append(init)
