
import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.copies import breakLink, syncTags, broadcastTags

@app.route('/videos/breaklink.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_breaklink(rd, user, data):
    print('break link')
    vid = data.video_id
    breakLink(vid, user)
    ret = makeResponseSuccess({})
    return "json", ret

@app.route('/videos/synctags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_synctags(rd, user, data):
    ret = syncTags(data.dst, data.src, user)
    if ret == 'SUCCEED':
        return "json", makeResponseSuccess({})
    else:
        return "json", makeResponseFailed(ret)

@app.route('/videos/broadcasttags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_broadcasttags(rd, user, data):
    ret = broadcastTags(data.src, user)
    if ret == 'SUCCEED':
        return "json", makeResponseSuccess({})
    else:
        return "json", makeResponseFailed(ret)
