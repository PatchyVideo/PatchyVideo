
import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch
from services.playlist import *

@app.route('/lists/new.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_new_do(rd, user, data):
    if len(data.title) > 128 or len(data.desc) > 2048 or len(data.cover) > 32 :
        return "json", makeResponseFailed("Data too large(max 128 chars for title, 2048 for description)")
    if not data.title or not data.desc :
        return "json", makeResponseFailed("Please fill all items")
    if data.pid :
        result = updatePlaylistInfo(data.pid, "english", data.title, data.desc, data.cover, user)
        if result == 'SUCCEED' :
            pid = data.pid
        else :
            return "json", result
    else :
        pid = createPlaylist("english", data.title, data.desc, data.cover, user)
    ret = makeResponseSuccess({
        "pid": pid
    })
    return "json", ret
