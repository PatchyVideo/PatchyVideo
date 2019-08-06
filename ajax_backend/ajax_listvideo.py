
import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch
from services.listVideo import listVideo, listVideoQuery


@app.route('/listvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_listvideo_do(rd, data, user):
    videos = listVideo(data.page - 1, data.page_size)
    video_count = videos.count()
    ret = makeResponseSuccess({
        "videos": [i for i in videos],
        "count": video_count,
        "page_count": (video_count - 1) // data.page_size + 1
    })
    return "json", ret

@app.route('/queryvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_queryvideo_do(rd, data, user):
    if len(data.query) > 1000 :
        return "json", makeResponseError("Query too long(max 1000 characters)")
    status, videos = listVideoQuery(data.query, data.page - 1, data.page_size)
    if status == "failed":
        return "json", makeResponseError("Syntax error in query")
    video_count = videos.count()
    ret = makeResponseSuccess({
        "videos": [i for i in videos],
        "count": video_count,
        "page_count": (video_count - 1) // data.page_size + 1
    })
    return "json", ret

