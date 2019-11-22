import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session, abort

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.getVideo import getVideoDetail, getTagCategories
from services.playlist import listPlaylistsForVideo
from config import TagsConfig, VideoConfig

@app.route('/getvideo', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_getvideo(rd, user, data):
    try:
        obj = getVideoDetail(data.vid)
    except:
        obj = None
    if not obj:
        abort("No such video id=%s" % data.vid, 404)
    tag_by_category = getTagCategories(obj['tags'])
    for category in tag_by_category :
        tag_by_category[category] = list(sorted(tag_by_category[category]))
    copies = []
    for item in obj['item']['copies'] :
        try:
            ver = getVideoDetail(item)
        except :
            ver = None
        if ver is not None :
            copies.append(ver)
    playlists = listPlaylistsForVideo(data.vid)
    return "json", makeResponseSuccess({
        "video" : obj,
        "tag_by_category" : tag_by_category,
        "copies" : copies,
        "playlists" : playlists
    })
