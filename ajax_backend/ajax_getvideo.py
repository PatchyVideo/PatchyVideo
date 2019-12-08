import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session, abort

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.getVideo import getVideoDetail
from services.playlist import listPlaylistsForVideo
from config import TagsConfig, VideoConfig

"""
@app.route('/getvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_getvideo(rd, user, data):
    obj, tags = getVideoDetailWithTagObjects(data.vid)
    copies = []
    for item in obj['item']['copies'] :
        ver = getVideoDetail(item)
        assert ver
        copies.append(ver)
    playlists = listPlaylistsForVideo(data.vid)
    return "json", makeResponseSuccess({
        "video" : obj,
        "tags" : tags,
        "copies" : copies,
        "playlists" : playlists
    })
"""
