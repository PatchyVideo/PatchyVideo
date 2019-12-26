
import time

from flask import render_template, request, jsonify, redirect, session

from db import tagdb
from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.tagtools import translateTagsToPreferredLanguage, getTagObjects
from services.playlist import *
from utils.html import buildPageSelector

@app.route('/list/getcommontags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_playlist_getcommontags_do(rd, data, user):
	tags = listCommonTags(data.pid, 'CHS')
	return "json", makeResponseSuccess(tags)

@app.route('/list/setcommontags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_setcommontags_do(rd, user, data):
	updateCommonTags(data.pid, data.tags, user)

@app.route('/list/setcover.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_setcover_do(rd, user, data):
	new_list = updatePlaylistCoverVID(data.pid, data.vid, int(data.page), int(data.page_size), user)
	return "json", makeResponseSuccess(new_list)

@app.route('/list/delete.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_deletevideo_do(rd, user, data):
	new_list = removeVideoFromPlaylist(data.pid, data.vid, int(data.page), int(data.page_size), user)
	return "json", makeResponseSuccess(new_list)

@app.route('/list/moveup.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_moveup_do(rd, user, data):
	new_list = editPlaylist_MoveUp(data.pid, data.vid, int(data.page), int(data.page_size), user)
	return "json", makeResponseSuccess(new_list)

@app.route('/list/movedown.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_movedown_do(rd, user, data):
	new_list = editPlaylist_MoveDown(data.pid, data.vid, int(data.page), int(data.page_size), user)
	return "json", makeResponseSuccess(new_list)

@app.route('/lists/new.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_new_do(rd, user, data):
	private = data.private if 'private' in data.__dict__ is not None else False
	if data.pid :
		updatePlaylistInfo(data.pid, "english", data.title, data.desc, data.cover, user, private)
		return "json", makeResponseSuccess({"pid": data.pid})
	else :
		pid = createPlaylist("english", data.title, data.desc, data.cover, user, private)
		return "json", makeResponseSuccess({"pid": pid})

@app.route('/lists/myplaylists', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_myplaylists(rd, user, data):
	page_size = int(data.page_size) if 'page_size' in data.__dict__ is not None else 10000
	page = (int(data.page) - 1) if 'page' in data.__dict__ is not None else 0
	order = data.order if 'order' in data.__dict__ is not None and data.order else 'last_modified'
	result = [item for item in listMyPlaylists(user, page, page_size, order)]
	return "json", makeResponseSuccess(result)

@app.route('/lists/all.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_all_do(rd, user, data):
	page_size = int(data.page_size) if 'page_size' in data.__dict__ is not None else 10000
	page = (int(data.page) - 1) if 'page' in data.__dict__ is not None else 0
	order = data.order if 'order' in data.__dict__ is not None and data.order else 'last_modified'
	playlists, playlists_count = listPlaylists(page, page_size, {}, order)
	result = [item for item in playlists]
	return "json", makeResponseSuccess({
		"playlists": result,
		"count": playlists_count,
		"page_count": (playlists_count - 1) // page_size + 1
		})

@app.route('/lists/get_playlist.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_get_playlist_do(rd, user, data):
	page_size = int(data.page_size) if 'page_size' in data.__dict__ is not None else 10000
	page = (int(data.page) - 1) if 'page' in data.__dict__ is not None else 0
	if user:
		videos, video_count, rd.playlist_editable = listPlaylistVideosWithAuthorizationInfo(data.pid, page, page_size, user)
	else:
		videos, video_count = listPlaylistVideos(data.pid, page, page_size)
	playlist = getPlaylist(data.pid)
	return "json", makeResponseSuccess({
		"playlist": playlist,
		"videos": [item for item in videos],
		"count": video_count,
		"page_count": (video_count - 1) // page_size + 1
		})

@app.route('/lists/create_from_copies.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_create_from_copies_do(rd, user, data):
	pid = createPlaylistFromCopies(data.pid, data.site, user)
	return "json", makeResponseSuccess(pid)
