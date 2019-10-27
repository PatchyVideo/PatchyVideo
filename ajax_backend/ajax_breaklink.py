
import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.breakLink import breakLink

@app.route('/videos/breaklink.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_breaklink(rd, user, data):
    vid = data.video_id
    breakLink(vid, user)
    ret = makeResponseSuccess({})
    return "json", ret

