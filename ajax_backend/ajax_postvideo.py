
import time
import os
import sys
import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app, rdb
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON, loginRequiredFallbackJSON
from utils.jsontools import *
from utils.http import post_raw
from utils.exceptions import UserError
from bson.json_util import dumps, loads

from services.postVideo import postVideo, postVideoBatch, listCurrentTasksWithParams, listFailedPosts, postVideoIPFS_new
from config import VideoConfig, TagsConfig

@app.route('/postvideo.do', methods = ['POST'])
@loginRequiredFallbackJSON
@jsonRequest
def ajax_postvideo_do(rd, user, data):
	dst_copy = getDefaultJSON(data, 'copy', '')
	dst_playlist = getDefaultJSON(data, 'pid', '')
	dst_rank = getDefaultJSON(data, 'rank', -1)
	repost_type = getDefaultJSON(data, 'repost_type', 'repost')
	if repost_type not in ['official', 'official_repost', 'authorized_translation', 'authorized_repost', 'translation', 'repost', 'unknown'] :
		raise UserError('INCORRECT_REPOST_TYPE')
	task_id = postVideo(user, data.url, data.tags, dst_copy, dst_playlist, dst_rank, repost_type)
	return "json", makeResponseSuccess({"task_id": task_id})

@app.route('/postvideo_batch.do', methods = ['POST'])
@loginRequiredFallbackJSON
@jsonRequest
def ajax_postvideo_batch_do(rd, user, data):
	dst_copy = getDefaultJSON(data, 'copy', '')
	dst_playlist = getDefaultJSON(data, 'pid', '')
	dst_rank = getDefaultJSON(data, 'rank', -1)
	as_copies = getDefaultJSON(data, 'as_copies', False)
	repost_type = getDefaultJSON(data, 'repost_type', 'repost')
	if repost_type not in ['official', 'official_repost', 'authorized_translation', 'authorized_repost', 'translation', 'repost', 'unknown'] :
		raise UserError('INCORRECT_REPOST_TYPE')
	task_ids = postVideoBatch(user, data.videos, data.tags, dst_copy, dst_playlist, dst_rank, as_copies, repost_type)
	return "json", makeResponseSuccess({"task_ids": task_ids})

@app.route('/postvideo_ipfs.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_postvideo_ipfs_do(rd, user, data):
	dst_copy = getDefaultJSON(data, 'copy', '')
	dst_playlist = getDefaultJSON(data, 'pid', '')
	dst_rank = getDefaultJSON(data, 'rank', -1)
	desc = getDefaultJSON(data, 'desc', '')
	title = getDefaultJSON(data, 'title', '')
	file_key = getDefaultJSON(data, 'file_key', '')
	original_url = getDefaultJSON(data, 'original_url', '')
	repost_type = getDefaultJSON(data, 'repost_type', 'repost')
	if repost_type not in ['official', 'official_repost', 'authorized_translation', 'authorized_repost', 'translation', 'repost', 'unknown'] :
		raise UserError('INCORRECT_REPOST_TYPE')
	if desc and title and file_key  :
		task_id = postVideoIPFS_new(user, data.url, data.tags, dst_copy, dst_playlist, dst_rank, desc, title, file_key, repost_type)
		return "json", makeResponseSuccess({"task_id": task_id})
	elif original_url :
		pass
	raise UserError('INCORRECT_IPFS_UPLOAD')

@app.route('/posts/list_pending.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_post_list_pending_do(rd, user, data):
	result = listCurrentTasksWithParams(user, int(data.page) - 1, int(data.page_size))
	return "json", makeResponseSuccess(result)

@app.route('/posts/list_failed.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_post_list_failed_do(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	result, counts = listFailedPosts(user, page, page_size)
	return "json", makeResponseSuccess({
		"posts": result,
		"count": counts,
		"page": page + 1,
		"page_count": (counts - 1) // page_size + 1,
	})
