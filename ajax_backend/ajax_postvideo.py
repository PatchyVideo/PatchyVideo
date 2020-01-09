
import time
import os
import sys
import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app, rdb
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.http import post_raw
from bson.json_util import dumps, loads

from services.postVideo import postVideo, postVideoBatch, listCurrentTasksWithParams, listFailedPosts
from config import VideoConfig, TagsConfig

@app.route('/postvideo.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_postvideo_do(rd, user, data):
	dst_copy = getDefaultJSON(data, 'copy', '')
	dst_playlist = getDefaultJSON(data, 'pid', '')
	dst_rank = getDefaultJSON(data, 'rank', -1)
	task_id = postVideo(user, data.url, data.tags, dst_copy, dst_playlist, dst_rank)
	return "json", makeResponseSuccess({"task_id": task_id})

@app.route('/postvideo_batch.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_postvideo_batch_do(rd, user, data):
	dst_copy = getDefaultJSON(data, 'copy', '')
	dst_playlist = getDefaultJSON(data, 'pid', '')
	dst_rank = getDefaultJSON(data, 'rank', -1)
	as_copies = getDefaultJSON(data, 'as_copies', False)
	task_ids = postVideoBatch(user, data.videos, data.tags, dst_copy, dst_playlist, dst_rank, as_copies)
	return "json", makeResponseSuccess({"task_ids": task_ids})

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
	result = listFailedPosts(user, page, page_size)
	return "json", makeResponseSuccess(result)
