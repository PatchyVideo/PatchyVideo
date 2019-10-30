import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.editVideo import editVideoTags, verifyTags, getVideoTags

@app.route('/videos/edittags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_edittags(rd, user, data):
    if len(data.tags) > 200 :
        return "json", makeResponseFailed("Too many tags, max 200 tags per video")
    for tag in data.tags :
        if len(tag) > 48 :
            return "json", makeResponseFailed("Tag length too large(48 characters max)")
    tags_ret, unrecognized_tag = verifyTags(data.tags)
    if tags_ret == 'TAG_NOT_EXIST':
        return "json", makeResponseFailed("Tag %s not recognized" % unrecognized_tag)
    retval = editVideoTags(data.video_id, data.tags, user)
    if retval == 'ITEM_NOT_EXIST':
        return "json", makeResponseFailed("Video %s does not exist" % data.video_id)
    return "json", makeResponseSuccess("Success")

@app.route('/videos/gettags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_videos_gettags(rd, user, data):
    ret, tags = getVideoTags(data.video_id)
    if ret == 'ITEM_NOT_EXIST' :
        return "json", makeResponseFailed("Video %s does not exist" % data.video_id)
    return "json", makeResponseSuccess(tags)
