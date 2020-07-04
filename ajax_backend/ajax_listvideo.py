
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError

from services.listVideo import listVideo, listVideoQuery, listMyVideo, listYourVideo
from services.tagStatistics import getCommonTagsWithCount
from services.getVideo import getTagCategoryMap
from config import QueryConfig

@app.route('/listvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_listvideo_do(rd, data, user):
	start = time.time()
	order = getDefaultJSON(data, 'order', 'latest')
	additional_constraint = getDefaultJSON(data, 'additional_constraint', '')
	hide_placeholder = getDefaultJSON(data, 'hide_placeholder', True)
	lang = getDefaultJSON(data, 'lang', 'CHS')
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise AttributeError()
	videos, video_count, related_tags, related_tags_popularity, query_obj, exStats1, exStats2 = listVideo(
		data.page - 1,
		data.page_size,
		user,
		order,
		hide_placeholder = hide_placeholder,
		user_language = lang,
		additional_constraint = additional_constraint)
	tag_category_map = getTagCategoryMap(related_tags)
	end = time.time()
	ret = makeResponseSuccess({
		"videos": videos,
		"count": video_count,
		"page_count": (video_count - 1) // data.page_size + 1,
		"tags": tag_category_map,
		"tag_pops": related_tags_popularity,
		'time_used_ms': int((end - start) * 1000),
		"query_obj": query_obj#,
		# "ex_stats_1": exStats1,
		# "ex_stats_2": exStats2
	})
	return "json", ret

@app.route('/queryvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_queryvideo_do(rd, data, user):
	start = time.time()
	if len(data.query) > QueryConfig.MAX_QUERY_LENGTH :
		raise UserError('QUERY_TOO_LONG')
	additional_constraint = getDefaultJSON(data, 'additional_constraint', '')
	order = getDefaultJSON(data, 'order', 'latest')
	qtype = getDefaultJSON(data, 'qtype', 'tag')
	lang = getDefaultJSON(data, 'lang', 'CHS')
	hide_placeholder = getDefaultJSON(data, 'hide_placeholder', True)
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise AttributeError()
	videos, related_tags, video_count, query_obj, exStats1, exStats2 = listVideoQuery(
		user,
		data.query,
		data.page - 1,
		data.page_size,
		order,
		hide_placeholder = hide_placeholder,
		qtype = qtype,
		user_language = lang,
		additional_constraint = additional_constraint)
	tag_category_map = getTagCategoryMap(related_tags)
	end = time.time()
	ret = makeResponseSuccess({
		"videos": [i for i in videos],
		"count": video_count,
		"page_count": (video_count - 1) // data.page_size + 1,
		"tags": tag_category_map,
		'time_used_ms': int((end - start) * 1000),
		"query_obj": query_obj#,
		# "ex_stats_1": exStats1,
		# "ex_stats_2": exStats2
	})
	return "json", ret

@app.route('/listmyvideo.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_listmyvideo_do(rd, data, user):
	order = getDefaultJSON(data, 'order', 'latest')
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise AttributeError()
	videos, video_count = listMyVideo(data.page - 1, data.page_size, user, order)
	ret = makeResponseSuccess({
		"videos": videos,
		"count": video_count,
		"tags": getCommonTagsWithCount(data.lang, videos),
		"page_count": (video_count - 1) // data.page_size + 1,
	})
	return "json", ret

@app.route('/listyourvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_listyourvideo_do(rd, data, user):
	order = getDefaultJSON(data, 'order', 'latest')
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise AttributeError()
	videos, video_count = listYourVideo(data.uid, data.page - 1, data.page_size, user, order)
	ret = makeResponseSuccess({
		"videos": videos,
		"count": video_count,
		"tags": getCommonTagsWithCount(data.lang, videos),
		"page_count": (video_count - 1) // data.page_size + 1,
	})
	return "json", ret
