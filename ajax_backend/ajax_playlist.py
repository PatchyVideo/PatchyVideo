
import time
import re

from flask import render_template, request, jsonify, redirect, session, abort

from db import tagdb
from init import app
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.tagtools import translateTagsToPreferredLanguage, getTagObjects
from services.playlist import *
from utils.html import buildPageSelector

@app.route('/list/getcommontags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_playlist_getcommontags_do(rd, data, user):
	tags = listCommonTags(user, data.pid, 'CHS')
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
	private = getDefaultJSON(data, 'private', False)
	if hasattr(data, 'pid') and data.pid :
		updatePlaylistInfo(data.pid, "english", data.title, data.desc, data.cover, user, private)
		return "json", makeResponseSuccess({"pid": data.pid})
	else :
		pid = createPlaylist("english", data.title, data.desc, data.cover, user, private)
		return "json", makeResponseSuccess({"pid": pid})

@app.route('/lists/myplaylists', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_myplaylists(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	order = getDefaultJSON(data, 'order', 'last_modified')
	playlists, playlists_count = listMyPlaylists(user, page, page_size, order)
	result = [item for item in playlists]
	return "json", makeResponseSuccess({
		"playlists": result,
		"count": playlists_count,
		"page_count": (playlists_count - 1) // page_size + 1
		})

@app.route('/lists/yourplaylists', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_yourplaylists(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	order = getDefaultJSON(data, 'order', 'last_modified')
	playlists, playlists_count = listYourPlaylists(user, data.uid, page, page_size, order)
	result = [item for item in playlists]
	return "json", makeResponseSuccess({
		"playlists": result,
		"count": playlists_count,
		"page_count": (playlists_count - 1) // page_size + 1
		})

@app.route('/lists/all.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_all_do(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	order = getDefaultJSON(data, 'order', 'last_modified')
	playlists, playlists_count = listPlaylists(user, page, page_size, {}, order)
	result = [item for item in playlists]
	return "json", makeResponseSuccess({
		"playlists": result,
		"count": playlists_count,
		"page_count": (playlists_count - 1) // page_size + 1
		})

@app.route('/lists/search.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_search_do(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	order = getDefaultJSON(data, 'order', 'last_modified')
	query = getDefaultJSON(data, 'query', '')
	# TODO: temporary solution, full text search index needed
	if query :
		keywords = query.split()
		keywords = [re.escape(q) for q in keywords]
		#search_regex = ''.join(['(?=.*%s)' % q for q in keywords])
		search_regex = '|'.join(keywords)
		search_regex = f'({search_regex})'
		query_obj = {'$or':[{'title.english': {'$regex': search_regex}}, {'desc.english': {'$regex': search_regex}}]}
	else :
		query_obj = {}
	playlists, playlists_count = listPlaylists(user, page, page_size, query_obj, order)
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
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	playlist = getPlaylist(data.pid)
	if playlist["private"] and str(playlist["meta"]["created_by"]) != str(user['_id']) :
		abort(404)
	playlist_editable = False
	if user:
		videos, video_count, playlist_editable = listPlaylistVideosWithAuthorizationInfo(data.pid, page, page_size, user)
	else:
		videos, video_count = listPlaylistVideos(data.pid, page, page_size, user)
	return "json", makeResponseSuccess({
		"editable": playlist_editable,
		"playlist": playlist,
		"videos": [item for item in videos],
		"count": video_count,
		"page_count": (video_count - 1) // page_size + 1
		})

@app.route('/lists/get_playlist_metadata.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_get_playlist_metadata_do(rd, user, data):
	playlist = getPlaylist(data.pid)
	if playlist["private"] and str(playlist["meta"]["created_by"]) != str(user['_id']) :
		abort(404)
	playlist_editable = False
	if user:
		playlist_editable = isAuthorised(playlist, user)
	return "json", makeResponseSuccess({
		"editable": playlist_editable,
		"playlist": playlist
		})

@app.route('/lists/update_playlist_metadata.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_update_playlist_metadata_do(rd, user, data):
	updatePlaylistInfo(data.pid, 'english', data.title, data.desc, None, user)

@app.route('/lists/del_playlist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_del_playlist_do(rd, user, data):
	removePlaylist(data.pid, user)

@app.route('/lists/create_from_copies.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_create_from_copies_do(rd, user, data):
	pid = createPlaylistFromCopies(data.pid, data.site, user)
	return "json", makeResponseSuccess(pid)

@app.route('/lists/create_from_video.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_create_from_video_do(rd, user, data):
	pid = createPlaylistFromSingleVideo('english', data.vid, user)
	return "json", makeResponseSuccess(pid)

@app.route('/lists/create_from_existing_playlists.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_create_from_existing_playlists(rd, user, data):
	new_playlist_id, task_id = createPlaylistFromExistingPlaylist('english', data.url, user)
	return "json", makeResponseSuccess({'pid': new_playlist_id, 'task_id': task_id})
