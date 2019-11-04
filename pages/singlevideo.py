
import time

from flask import render_template, request, jsonify, redirect, session, abort

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
        abort("No such video id=%s" % vidid, 404)
    rd.thumbnail_url = obj['item']['thumbnail_url']
    rd.cover_image = obj['item']['cover_image']
    rd.title = obj['item']['title']
    rd.desc = obj['item']['desc']
    rd.link = obj['item']['url']
    rd.upload_date = obj['item']['upload_time'] if 'upload_time' in obj['item'] else ''
    if not rd.upload_date:
        rd.upload_date = ''
    rd.tags = ' '.join(obj['tags'])
    rd.tags_list = obj['tags']
    rd.tag_by_category = getTagCategories(rd.tags_list)
    for category in rd.tag_by_category :
        rd.tag_by_category[category] = list(sorted(rd.tag_by_category[category]))
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


