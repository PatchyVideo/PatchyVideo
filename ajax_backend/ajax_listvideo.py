
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError

from spiders import dispatch
from services.listVideo import listVideo, listVideoQuery
from services.getVideo import getTagCategoryMap
from config import QueryConfig

@app.route('/listvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_listvideo_do(rd, data, user):
	videos, related_tags = listVideo(data.page - 1, data.page_size)
	tag_category_map = getTagCategoryMap(related_tags)
	video_count = videos.count()
	ret = makeResponseSuccess({
		"videos": [i for i in videos],
		"count": video_count,
		"page_count": (video_count - 1) // data.page_size + 1,
		"tags": tag_category_map
	})
	return "json", ret

@app.route('/queryvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_queryvideo_do(rd, data, user):
	if len(data.query) > QueryConfig.MAX_QUERY_LENGTH :
		raise UserError('QUERY_TOO_LONG')
	videos, related_tags, video_count = listVideoQuery(data.query, data.page - 1, data.page_size)
	tag_category_map = getTagCategoryMap(related_tags)
	ret = makeResponseSuccess({
		"videos": [i for i in videos],
		"count": video_count,
		"page_count": (video_count - 1) // data.page_size + 1,
		"tags": tag_category_map
	})
	return "json", ret

