
import time

from flask import render_template, request, jsonify, redirect, session, abort

from init import app
from utils.interceptors import loginOptional, loginRequired
from services.playlist import *
from services.user import query_user_basic_info
from utils.html import buildPageSelector
from config import DisplayConfig

@app.route('/lists/new')
@loginRequired
def pages_create_playlist(rd, user):
	"""
	rd.default_tags = ''
	rd.copy = ''
	if 'copy' in request.values:
		vid = request.values['copy']
		try:
			obj = getVideoDetail(vid)
		except:
			obj = None
		if obj is not None:
			rd.default_tags = '\n'.join(obj['tags'])
			rd.copy = vid
	"""
	return "create_playlist.html"

@app.route('/lists/newfromsinglevideo.do')
@loginRequired
def pages_create_playlist_from_single_video(rd, user):
	if 'vid' in request.values:
		vid = request.values['vid']
		new_pid = createPlaylistFromSingleVideo("english", vid, user)
		return 'redirect', '/list/%s/' % new_pid
	else:
		abort(400)

@app.route('/list/<pid>/edit')
@loginRequired
def pages_edit_playlist(pid, rd, user):
	rd.pid = pid
	playlist = getPlaylist(pid)
	rd.title = playlist['title']['english']
	rd.desc = playlist['desc']['english']
	return "create_playlist.html"

@app.route('/list/<pid>/', methods = ['GET', 'POST'])
@loginOptional
def pages_playlist(pid, rd, user):
	try :
		ObjectId(pid)
	except:
		abort(404)
	rd.page = int(request.values['page'] if 'page' in request.values else 1)
	rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
	if rd.page_size > DisplayConfig.MAX_ITEM_PER_PAGE :
		return "data", 'Page size too large(max %d videos per page)' % DisplayConfig.MAX_ITEM_PER_PAGE
	rd.order = "latest"
	rd.playlist_editable = False
	if user:
		videos, video_count, rd.playlist_editable = listPlaylistVideosWithAuthorizationInfo(pid, rd.page - 1, rd.page_size, user)
	else:
		videos, video_count = listPlaylistVideos(pid, rd.page - 1, rd.page_size)
	playlist = getPlaylist(pid)
	rd.playlist_title = playlist['title']['english']
	rd.playlist_desc = playlist['desc']['english']
	rd.playlist_id = playlist['_id']
	rd.playlist_creator = str(playlist['meta']['created_by'])
	rd.playlist_creator_info = query_user_basic_info(rd.playlist_creator)
	rd.playlist_cover_image = playlist['cover']
	rd.videos = videos
	rd.count = video_count
	rd.page_count = (video_count - 1) // rd.page_size + 1
	rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
	return 'content_playlist.html'

@app.route('/list/<pid>/add', methods = ['GET'])
@loginRequired
def pages_playlist_addvideo(pid, rd, user):
	rd.copy = ''
	rd.pid = pid
	rd.default_tags = '\n'.join(listCommonTags(pid, 'CHS'))
	return "postvideo.html"

@app.route('/list/<pid>/del', methods = ['GET'])
@loginRequired
def pages_playlist_delplaylist(pid, rd, user):
	removePlaylist(pid, user)
	return "redirect", "/lists"

@app.route('/list/<pid>/insert', methods = ['GET'])
@loginRequired
def pages_playlist_insertvideo(pid, rd, user):
	rd.copy = ''
	rd.pid = pid
	rd.rank = -1
	rd.default_tags = '\n'.join(listCommonTags(pid, 'CHS'))
	if 'rank' in request.values:
		try:
			rd.rank = int(request.values['rank'])
		except:
			pass
	return "postvideo.html"

