
import time

from flask import render_template, request, jsonify, redirect, session

from main import app
from utils.interceptors import loginOptional
from utils.html import buildPageSelector
from services.listVideo import listVideo, listVideoQuery

@app.route('/search', methods = ['POST', 'GET'])
@loginOptional
def pages_search(rd, user):
    rd.page = int(request.values['page'] if 'page' in request.values else 1)
    rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
    if rd.page_size > 500 :
        rd.reason = 'Page size too large(max 500 videos per page)'
        return 'content_videolist_failed.html'
    rd.query = request.values['query'] if 'query' in request.values else ""
    rd.order = "latest"
    #return 'content_videolist.html'
    if rd.query :
        if len(rd.query) > 256:
            rd.reason = 'Query too long(max 256 characters)'
            return 'content_videolist_failed.html'
        status, videos, related_tags = listVideoQuery(rd.query, rd.page - 1, rd.page_size)
    else :
        videos, related_tags = listVideo(rd.page - 1, rd.page_size)
        status = "succeed"
    if status == "failed":
        rd.reason = "Syntax error in query"
        return 'content_videolist_failed.html'
    video_count = len(videos)
    rd.videos = videos
    rd.count = video_count
    rd.tags_list = related_tags
    rd.page_count = (video_count - 1) // rd.page_size + 1
    rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
    return 'content_videolist.html'


