
import time

from flask import render_template, request, jsonify, redirect, session

from main import app
from utils.interceptors import loginOptional, loginRequired

from services.getVideo import getVideoDetail

@app.route('/postvideo')
@loginRequired
def pages_postvideo(rd, user):
    rd.default_tags = ''
    rd.copy = ''
    rd.pid = ''
    rd.rank = -1
    if 'copy' in request.values:
        vid = request.values['copy']
        try:
            obj = getVideoDetail(vid)
        except:
            obj = None
        if obj is not None:
            rd.default_tags = '\n'.join(obj['tags'])
            rd.copy = vid
    if 'use_tags' in request.values:
        vid = request.values['use_tags']
        try:
            obj = getVideoDetail(vid)
        except:
            obj = None
        if obj is not None:
            rd.default_tags = '\n'.join(obj['tags'])
    return "postvideo.html"


