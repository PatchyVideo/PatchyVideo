
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
from services.postVideo import postVideo, postVideoBatch, listCurrentTasksWithParams, listFailedPosts
from config import VideoConfig, TagsConfig

@app.route('/postvideo.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_postvideo_do(rd, user, data):
	dst_copy = data.copy if 'copy' in data.__dict__ and data.copy is not None else ''
	dst_playlist = data.pid if 'pid' in data.__dict__ and data.pid is not None else ''
	dst_rank = int(data.rank if 'rank' in data.__dict__ and data.rank is not None else -1)
	task_id = postVideo(user, data.url, data.tags, dst_copy, dst_playlist, dst_rank)
	return "json", makeResponseSuccess({"task_id": task_id})

@app.route('/postvideo_batch.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_postvideo_batch_do(rd, user, data):
	dst_copy = data.copy if 'copy' in data.__dict__ and data.copy is not None else ''
	dst_playlist = data.pid if 'pid' in data.__dict__ and data.pid is not None else ''
	dst_rank = int(data.rank if 'rank' in data.__dict__ and data.rank is not None else -1)
	as_copies = data.as_copies if 'as_copies' in data.__dict__ and data.as_copies is not None else False
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
	result = listFailedPosts(user, int(data.page) - 1, int(data.page_size))
	return "json", makeResponseSuccess(result)
