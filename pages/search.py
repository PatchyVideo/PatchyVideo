
import time

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional
from utils.html import buildPageSelector
from utils.tagtools import getTagColor
from utils.exceptions import UserError
from services.listVideo import listVideo, listVideoQuery
from services.getVideo import getTagCategoryMap
from config import DisplayConfig, QueryConfig

@app.route('/search', methods = ['POST', 'GET'])
@loginOptional
def pages_search(rd, user):
	rd.page = int(request.values['page'] if 'page' in request.values else 1)
	if rd.page < 1:
		rd.reason = 'page must be greater than or equals to 1'
		return 'content_videolist_failed.html'
	rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
	if rd.page_size > DisplayConfig.MAX_ITEM_PER_PAGE :
		rd.reason = 'Page size too large(max %d videos per page)' % DisplayConfig.MAX_ITEM_PER_PAGE
		return 'content_videolist_failed.html'
	if rd.page_size < 1:
		rd.reason = 'Page size must be greater than or equals to 1'
		return 'content_videolist_failed.html'
	rd.order = (request.values['order'] if 'order' in request.values else 'latest')
	if not rd.order in ['latest', 'oldest', 'video_latest', 'video_oldest']:
		rd.reason = 'order must be one of latest,oldest,video_latest,video_oldest'
		return 'content_videolist_failed.html'
	
	rd.query = request.values['query'] if 'query' in request.values else ""
	rd.hide_placeholder = (int(request.values['hide_placeholder']) != 0) if 'hide_placeholder' in request.values else True
	#return 'content_videolist.html'
	if rd.query :
		if len(rd.query) > QueryConfig.MAX_QUERY_LENGTH:
			rd.reason = 'Query too long(max %d characters)' % QueryConfig.MAX_QUERY_LENGTH
			return 'content_videolist_failed.html'
		try :
			videos, related_tags, video_count = listVideoQuery(rd.query, rd.page - 1, rd.page_size, rd.order, hide_placeholder = rd.hide_placeholder)
		except UserError as ue :
			if ue.msg == 'INCORRECT_QUERY' :
				rd.reason = "Syntax error in query"
				return 'content_videolist_failed.html'
			elif ue.msg == 'FAILED_NOT_OP' :
				rd.reason = "NOT operator can only be applied to tags"
				return 'content_videolist_failed.html'
			elif ue.msg == 'FAILED_UNKNOWN' :
				rd.reason = "Unknown error"
				return 'content_videolist_failed.html'
		rd.videos = videos
	else :
		videos, related_tags = listVideo(rd.page - 1, rd.page_size, rd.order)
		video_count = videos.count()
		rd.videos = [item for item in videos]

	rd.count = video_count
	tag_category_map = getTagCategoryMap(related_tags)
	tag_color_map = getTagColor(related_tags, tag_category_map)
	rd.tags_list = tag_color_map
	rd.title = 'Search'
	rd.page_count = (video_count - 1) // rd.page_size + 1
	rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
	return 'content_videolist.html'


