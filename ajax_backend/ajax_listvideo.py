
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON, getOffsetLimitJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError

from services.listVideo import listVideo, listVideoQuery, listMyVideo, listYourVideo, listVideoRandimzied
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
	human_readable_tag = getDefaultJSON(data, 'human_readable_tag', False)
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise AttributeError()
	offset, limit = getOffsetLimitJSON(data)
	videos, video_count, related_tags, related_tags_popularity, query_obj, exStats1, exStats2 = listVideo(
		offset,
		limit,
		user,
		order,
		hide_placeholder = hide_placeholder,
		user_language = lang,
		additional_constraint = additional_constraint,
		human_readable_tag = human_readable_tag)
	tag_category_map = getTagCategoryMap(related_tags)
	end = time.time()
	ret = makeResponseSuccess({
		"videos": videos,
		"count": video_count,
		"page_count": (video_count - 1) // limit + 1,
		"tags": tag_category_map,
		"tag_pops": related_tags_popularity,
		'time_used_ms': int((end - start) * 1000),
		"query_obj": query_obj#,
		# "ex_stats_1": exStats1,
		# "ex_stats_2": exStats2
	})
	return "json", ret

@app.route('/listvideo_randomized.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_listvideo_randomized_do(rd, data, user):
	query = getDefaultJSON(data, 'query', '')
	if len(query) > QueryConfig.MAX_QUERY_LENGTH :
		raise UserError('QUERY_TOO_LONG')
	additional_constraint = getDefaultJSON(data, 'additional_constraint', '')
	human_readable_tag = getDefaultJSON(data, 'human_readable_tag', False)
	qtype = getDefaultJSON(data, 'qtype', 'tag')
	lang = getDefaultJSON(data, 'lang', 'CHS')
	_, limit = getOffsetLimitJSON(data)
	videos, related_tags = listVideoRandimzied(
		user,
		limit,
		query,
		lang,
		qtype,
		additional_constraint,
		human_readable_tag)
	tag_category_map = getTagCategoryMap(related_tags)
	ret = makeResponseSuccess({
		"videos": videos,
		"tags": tag_category_map,
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
	human_readable_tag = getDefaultJSON(data, 'human_readable_tag', False)
	hide_placeholder = getDefaultJSON(data, 'hide_placeholder', True)
	offset, limit = getOffsetLimitJSON(data)
	videos, related_tags, video_count, query_obj, exStats1, exStats2 = listVideoQuery(
		user,
		data.query,
		offset,
		limit,
		order,
		hide_placeholder = hide_placeholder,
		qtype = qtype,
		user_language = lang,
		additional_constraint = additional_constraint,
		human_readable_tag = human_readable_tag)
	tag_category_map = getTagCategoryMap(related_tags)
	end = time.time()
	ret = makeResponseSuccess({
		"videos": videos,
		"count": video_count,
		"page_count": (video_count - 1) // limit + 1,
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
	lang = getDefaultJSON(data, 'lang', 'CHS')
	offset, limit = getOffsetLimitJSON(data)
	videos, video_count = listMyVideo(offset, limit, user, order, user_language = lang)
	ret = makeResponseSuccess({
		"videos": videos,
		"count": video_count,
		"tags": getCommonTagsWithCount(lang, videos),
		"page_count": (video_count - 1) // limit + 1,
	})
	return "json", ret

@app.route('/listyourvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_listyourvideo_do(rd, data, user):
	order = getDefaultJSON(data, 'order', 'latest')
	lang = getDefaultJSON(data, 'lang', 'CHS')
	offset, limit = getOffsetLimitJSON(data)
	videos, video_count = listYourVideo(data.uid, offset, limit, user, order, user_language = lang)
	ret = makeResponseSuccess({
		"videos": videos,
		"count": video_count,
		"tags": getCommonTagsWithCount(lang, videos),
		"page_count": (video_count - 1) // limit + 1,
	})
	return "json", ret
