
import time

from flask import render_template, request, jsonify, redirect, session, abort

from init import app
from utils.interceptors import loginOptional
from utils.tagtools import getTagColor
from services.listVideo import listVideo, listVideoQuery
from services.getVideo import getTagCategoryMap
from utils.html import buildPageSelector
from config import DisplayConfig

@app.route('/', methods = ['POST', 'GET'])
@loginOptional
def pages_index(rd, user):
	if user:
		return _renderRegisteredIndex(rd, user)
	else:
		return _renderAnonymousIndex(rd)

def _renderAnonymousIndex(rd):
	rd.page = int(request.values['page'] if 'page' in request.values else 1)
	if rd.page < 1:
		abort(400, 'page must be greater than or equals to 1')
	rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
	if rd.page_size > DisplayConfig.MAX_ITEM_PER_PAGE :
		abort(400, 'Page size too large(max %d videos per page)' % DisplayConfig.MAX_ITEM_PER_PAGE)
	if rd.page_size < 1:
		abort(400, 'Page size must be greater than or equals to 1')
	rd.order = request.values['order'] if 'order' in request.values else 'latest'
	if not rd.order in ['latest', 'oldest', 'video_latest', 'video_oldest']:
		abort(400, 'order must be one of latest,oldest,video_latest,video_oldest')
	rd.query = request.values['query'] if 'query' in request.values else ""
	rd.title = 'PatchyVideo'
	videos, tags = listVideo(rd.page - 1, rd.page_size, rd.order)
	video_count = videos.count()
	rd.is_hot = '热门'
	rd.videos = [item for item in videos]
	rd.count = video_count
	tag_category_map = getTagCategoryMap(tags)
	tag_color_map = getTagColor(tags, tag_category_map)
	rd.tags_list = tag_color_map
	rd.page_count = (video_count - 1) // rd.page_size + 1
	rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
	return 'content_videolist.html'

def _renderRegisteredIndex(rd, user):
	rd.page = int(request.values['page'] if 'page' in request.values else 1)
	if rd.page < 1:
		abort(400, 'page must be greater than or equals to 1')
	rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
	if rd.page_size > DisplayConfig.MAX_ITEM_PER_PAGE :
		abort(400, 'Page size too large(max %d videos per page)' % DisplayConfig.MAX_ITEM_PER_PAGE)
	if rd.page_size < 1:
		abort(400, 'Page size must be greater than or equals to 1')
	rd.order = request.values['order'] if 'order' in request.values else 'latest'
	if not rd.order in ['latest', 'oldest', 'video_latest', 'video_oldest']:
		abort(400, 'order must be one of latest,oldest,video_latest,video_oldest')
	rd.query = request.values['query'] if 'query' in request.values else ""
	rd.title = 'PatchyVideo'
	rd.is_hot = '热门'
	videos, tags = listVideo(rd.page - 1, rd.page_size, rd.order)
	video_count = videos.count()
	rd.videos = [item for item in videos]
	rd.count = video_count
	tag_category_map = getTagCategoryMap(tags)
	tag_color_map = getTagColor(tags, tag_category_map)
	rd.tags_list = tag_color_map
	rd.page_count = (video_count - 1) // rd.page_size + 1
	rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
	return 'content_videolist.html'
