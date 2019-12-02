
import time

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, loginRequired
from utils.tagtools import translateTagsToPreferredLanguage

from services.getVideo import getVideoDetailWithTagObjects

@app.route('/postvideo')
@loginRequired
def pages_postvideo(rd, user):
    rd.default_tags = ''
    rd.copy = ''
    rd.pid = ''
    rd.rank = -1
    if 'copy' in request.values:
        vid = request.values['copy']
        _, tag_objs = getVideoDetailWithTagObjects(vid)
        tags_translated = translateTagsToPreferredLanguage(tag_objs, 'CHS')
        rd.default_tags = '\n'.join(tags_translated)
        rd.copy = vid
    if 'use_tags' in request.values:
        vid = request.values['use_tags']
        _, tag_objs = getVideoDetailWithTagObjects(vid)
        tags_translated = translateTagsToPreferredLanguage(tag_objs, 'CHS')
        rd.default_tags = '\n'.join(tags_translated)
    return "postvideo.html"


