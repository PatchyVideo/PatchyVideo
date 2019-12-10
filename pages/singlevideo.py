
import time

from flask import render_template, request, jsonify, redirect, session, abort

from init import app
from utils.interceptors import loginOptional
from utils.exceptions import UserError
from utils.tagtools import translateTagsToPreferredLanguage

from services.getVideo import getVideoDetail, getVideoDetailWithTags
from services.playlist import listPlaylistsForVideo

@app.route('/video')
@loginOptional
def pages_videodetail(rd, user):
	vidid = request.values['id']
	try:
		obj, tags, category_tag_map, tag_category_map = getVideoDetailWithTags(vidid, 'CHS')
	except UserError:
		abort(404, "No such video id=%s" % vidid)
		
	rd.thumbnail_url = obj['item']['thumbnail_url']
	rd.cover_image = obj['item']['cover_image']
	rd.title = obj['item']['title']
	rd.desc = obj['item']['desc']
	rd.link = obj['item']['url']
	rd.upload_date = obj['item']['upload_time'] if 'upload_time' in obj['item'] else ''
	if not rd.upload_date:
		rd.upload_date = ''
	rd.tags = ' '.join(tags)
	rd.tags_list = tags
	rd.tag_by_category = category_tag_map
	for category in rd.tag_by_category :
		rd.tag_by_category[category] = list(sorted(rd.tag_by_category[category]))
	rd.video_id = vidid
	rd.copies = []
	for item in obj['item']['copies'] :
		ver = getVideoDetail(item)
		assert ver
		rd.copies.append(ver)
	rd.playlists = listPlaylistsForVideo(vidid)
	return "content_singlevideo.html"


