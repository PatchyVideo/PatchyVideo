
import time

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional
from utils.tagtools import getTagColor
from services.listVideo import listVideo, listVideoQuery
from services.getVideo import getTagCategoryMap
from utils.html import buildPageSelector


@app.route('/', methods = ['POST', 'GET'])
@loginOptional
def pages_index(rd, user):
    if user:
        return _renderRegisteredIndex(rd, user)
    else:
        return _renderAnonymousIndex(rd)

def _renderAnonymousIndex(rd):
    rd.page = int(request.values['page'] if 'page' in request.values else 1)
    rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
    rd.query = request.values['query'] if 'query' in request.values else ""
    rd.order = "latest"
    videos, tags = listVideo(rd.page - 1, rd.page_size)
    video_count = videos.count()
    rd.videos = [item for item in videos]
    rd.count = video_count
    tag_category_map = getTagCategoryMap(tags)
    tag_color_map = getTagColor(tag_category_map)
    rd.tags_list = tag_color_map
    rd.page_count = (video_count - 1) // rd.page_size + 1
    rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
    return 'content_videolist.html'

def _renderRegisteredIndex(rd, user):
    rd.page = int(request.values['page'] if 'page' in request.values else 1)
    rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
    rd.query = request.values['query'] if 'query' in request.values else ""
    rd.order = "latest"
    videos, tags = listVideo(rd.page - 1, rd.page_size)
    video_count = videos.count()
    rd.videos = [item for item in videos]
    rd.count = video_count
    tag_category_map = getTagCategoryMap(tags)
    tag_color_map = getTagColor(tag_category_map)
    rd.tags_list = tag_color_map
    rd.page_count = (video_count - 1) // rd.page_size + 1
    rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
    return 'content_videolist.html'
