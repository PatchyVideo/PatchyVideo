
import time

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, loginRequired
from db import tagdb

@app.route('/postvideo')
@loginRequired
def pages_postvideo(rd, user):
    rd.default_tags = ''
    rd.copy = ''
    rd.pid = ''
    rd.rank = -1
    if 'copy' in request.values:
        vid = request.values['copy']
        _, tags, _, _ = tagdb.retrive_item_with_tag_category_map(vid, 'CHS')
        rd.default_tags = '\n'.join(tags)
        rd.copy = vid
    if 'use_tags' in request.values:
        vid = request.values['use_tags']
        _, tags, _, _ = tagdb.retrive_item_with_tag_category_map(vid, 'CHS')
        rd.default_tags = '\n'.join(tags)
    return "postvideo.html"


