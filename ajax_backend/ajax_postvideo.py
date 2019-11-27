
import time
import os
import sys
import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app, rdb
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.http import post_raw
from bson.json_util import dumps, loads

from spiders import dispatch
from services.postVideo import postVideo, verifyTags
from config import VideoConfig, TagsConfig

if os.getenv("FLASK_ENV", "development") == "production" :
    SCRAPER_ADDRESS = 'http://scraper:5003'
else :
    SCRAPER_ADDRESS = 'http://localhost:5003'


def post_task(json_str) :
	ret_obj = loads(post_raw(SCRAPER_ADDRESS, json_str.encode('utf-8')).text)
	return ret_obj['task_id']

def create_json_for_posting(url, tags, dst_copy, dst_playlist, dst_rank, other_copies, user, playlist_ordered = None) :
	return dumps({
		'url' : url,
		'tags' : tags,
		'dst_copy' : dst_copy,
		'dst_playlist' : dst_playlist,
		'dst_rank' : dst_rank,
		'other_copies' : other_copies,
		'user' : user,
		'playlist_ordered' : playlist_ordered
	})

@app.route('/postvideo.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_postvideo_do(rd, user, data):
	if len(data.url) > VideoConfig.MAX_URL_LENGTH :
		return "json", makeResponseFailed("URL too long (max length %d)" % VideoConfig.MAX_URL_LENGTH)
	if len(data.tags) > VideoConfig.MAX_TAGS_PER_VIDEO :
		return "json", makeResponseFailed("Too many tags, max %d tags per video" % VideoConfig.MAX_TAGS_PER_VIDEO)
	for tag in data.tags :
		if len(tag) > TagsConfig.MAX_TAG_LENGTH :
			return "json", makeResponseFailed("Tag length too large(%d characters max)" % TagsConfig.MAX_TAG_LENGTH)
	obj, cleanURL = dispatch(data.url)
	if not cleanURL :
		return "json", makeResponseFailed("URL can't be empty")
	if obj is None:
		return "json", makeResponseFailed("Unsupported website")
	tags_ret, unrecognized_tag = verifyTags(data.tags)
	dst_copy = data.copy if 'copy' in data.__dict__ else ''
	dst_playlist = data.pid if 'pid' in data.__dict__ else ''
	dst_rank = data.rank if 'rank' in data.__dict__ else -1
	if tags_ret == 'TAG_NOT_EXIST':
		return "json", makeResponseFailed("Tag %s not recognized" % unrecognized_tag)
	task_id = post_task(create_json_for_posting(cleanURL, data.tags, dst_copy, dst_playlist, dst_rank, [], user))
	ret = makeResponseSuccess({
		"task_id": task_id
	})
	return "json", ret

@app.route('/postvideo_batch.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_postvideo_batch_do(rd, user, data):
	if len(data.videos) < 1 :
		return "json", makeResponseFailed("Please post at least 1 video")
	if len(data.videos) > VideoConfig.MAX_BATCH_POST_COUNT :
		return "json", makeResponseFailed("Too many videos, max %d per post" % VideoConfig.MAX_BATCH_POST_COUNT)
	if len(data.tags) > VideoConfig.MAX_TAGS_PER_VIDEO :
		return "json", makeResponseFailed("Too many tags, max %d tags per video" % VideoConfig.MAX_TAGS_PER_VIDEO)
	for tag in data.tags :
		if len(tag) > TagsConfig.MAX_TAG_LENGTH :
			return "json", makeResponseFailed("Tag length too large(%d characters max)" % TagsConfig.MAX_TAG_LENGTH)
	tags_ret, unrecognized_tag = verifyTags(data.tags)
	dst_copy = data.copy if 'copy' in data.__dict__ and data.copy is not None else ''
	dst_playlist = data.pid if 'pid' in data.__dict__ and data.pid is not None else ''
	dst_rank = int(data.rank if 'rank' in data.__dict__ and data.rank is not None else -1)
	as_copies = data.as_copies if 'as_copies' in data.__dict__ and data.as_copies is not None else False
	if tags_ret == 'TAG_NOT_EXIST':
		return "json", makeResponseFailed("Tag %s not recognized" % unrecognized_tag)
	succeed = True
	cleanURL_objs = []
	unique_ids = []
	for url in data.videos :
		url = url.strip()
		if not url:
			continue
		obj, cleanURL = dispatch(url)
		cleanURL_objs.append((obj, cleanURL))
		if obj is not None :
			unique_ids.append(obj.unique_id(obj, cleanURL))
	for idx, (url, (obj, cleanURL)) in enumerate(zip(data.videos, cleanURL_objs)) :
		print('Posting %s' % url, file = sys.stderr)
		if obj is None:
			succeed = False
		next_idx = idx if dst_rank >= 0 else 0
		task_id = post_task(create_json_for_posting(cleanURL, data.tags, dst_copy, dst_playlist, dst_rank + next_idx, unique_ids if as_copies else [], user, unique_ids))
	if succeed :
		ret = makeResponseSuccess({
			"task_id": task_id
		})
	else :
		ret =  makeResponseFailed("Unsupported website")
	return "json", ret
