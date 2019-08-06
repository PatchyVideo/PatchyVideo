
import time

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional

from services.getVideo import getVideoDetail, getTagCategories
from services.playlist import listPlaylistsForVideo

@app.route('/video')
@loginOptional
def pages_videodetail(rd, user):
    vidid = request.values['id']
    try:
        obj = getVideoDetail(vidid)
    except:
        obj = None
    if not obj:
        return "data", "No such video id=%s" % vidid
    rd.thumbnail_url = obj['item']['thumbnail_url']
    rd.cover_image = obj['item']['cover_image']
    rd.title = obj['item']['title']
    rd.desc = obj['item']['desc']
    rd.link = obj['item']['url']
    rd.tags = ' '.join(obj['tags'])
    rd.tags_list = obj['tags']
    rd.tag_by_category = getTagCategories(rd.tags_list)
    rd.video_id = vidid
    rd.copies = []
    for item in obj['item']['copies'] :
        try:
            ver = getVideoDetail(item)
        except :
            ver = None
        if ver is not None :
            rd.copies.append(ver)
    rd.playlists = listPlaylistsForVideo(vidid)
    return "content_singlevideo.html"


