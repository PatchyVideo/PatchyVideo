
import time
import re

from flask import render_template, request, jsonify, redirect, session, abort

from db import tagdb, playlist_db
from init import app
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.tagtools import translateTagsToPreferredLanguage, getTagObjects
from services.playlist import *
from utils.html import buildPageSelector

def _buildQueryObj(query) :
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
	return query_obj

def _buildQueryObjV2(query, additional_constraints) :
	pass

@app.route('/list/getcommontags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_playlist_getcommontags_do(rd, data, user):
	tags = listCommonTags(user, data.pid, data.lang)
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
	updatePlaylistCoverVID(data.pid, data.vid, int(data.page), int(data.page_size), user)

@app.route('/list/delete.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_deletevideo_do(rd, user, data):
	removeVideoFromPlaylist(data.pid, data.vid, int(data.page), int(data.page_size), user)

@app.route('/list/moveup.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_moveup_do(rd, user, data):
	editPlaylist_MoveUp(data.pid, data.vid, int(data.page), int(data.page_size), user)

@app.route('/list/movedown.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_movedown_do(rd, user, data):
	editPlaylist_MoveDown(data.pid, data.vid, int(data.page), int(data.page_size), user)

@app.route('/list/move.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_move_do(rd, user, data):
	editPlaylist_Move(data.pid, data.vid, data.rank, user)

@app.route('/list/inverse.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_inverse_do(rd, user, data):
	inversePlaylistOrder(data.pid, user)

@app.route('/list/set_tags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_set_tags_do(rd, user, data):
	updatePlaylistTags(data.pid, data.tags, user)

@app.route('/lists/new.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_new_do(rd, user, data):
	private = getDefaultJSON(data, 'private', False)
	privateEdit = getDefaultJSON(data, 'privateEdit', True)
	if hasattr(data, 'pid') and data.pid :
		updatePlaylistInfo(data.pid, data.title, data.desc, data.cover, user, private, privateEdit)
		return "json", makeResponseSuccess({"pid": data.pid})
	else :
		pid = createPlaylist(data.title, data.desc, data.cover, user, private, privateEdit)
		return "json", makeResponseSuccess({"pid": str(pid)})

@app.route('/lists/myplaylists', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_myplaylists(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	order = getDefaultJSON(data, 'order', 'last_modified')
	query = getDefaultJSON(data, 'query', '')
	query_obj = _buildQueryObj(query)
	playlists, playlists_count = listMyPlaylists(user, page, page_size, query_obj, order)
	return "json", makeResponseSuccess({
		"playlists": playlists,
		"count": playlists_count,
		"page_count": (playlists_count - 1) // page_size + 1
		})

@app.route('/lists/myplaylists_vid', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_myplaylists_vid(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	order = getDefaultJSON(data, 'order', 'last_modified')
	query = getDefaultJSON(data, 'query', '')
	query_obj = _buildQueryObj(query)
	playlists, playlists_count = listMyPlaylistsAgainstSingleVideo(user, data.vid, page, page_size, query_obj, order)
	return "json", makeResponseSuccess({
		"playlists": playlists,
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
	query = getDefaultJSON(data, 'query', '')
	query_obj = _buildQueryObj(query)
	playlists, playlists_count = listYourPlaylists(user, data.uid, page, page_size, query_obj, order)
	return "json", makeResponseSuccess({
		"playlists": playlists,
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
	playlists, playlists_count = listPlaylists(user, page, page_size, '', order, 'text', '')
	return "json", makeResponseSuccess({
		"playlists": playlists,
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
	additional_constraint = getDefaultJSON(data, 'additional_constraint', '')
	assert isinstance(query, str)
	playlists, playlists_count = listPlaylists(user, page, page_size, query, order, 'text', additional_constraint)
	return "json", makeResponseSuccess({
		"playlists": playlists,
		"count": playlists_count,
		"page_count": (playlists_count - 1) // page_size + 1
		})

@app.route('/lists/list.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_list_do(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	order = getDefaultJSON(data, 'order', 'last_modified')
	query = getDefaultJSON(data, 'query', '')
	additional_constraints = getDefaultJSON(data, 'additional_constraints', '')
	query_obj = _buildQueryObj(query)
	playlists, playlists_count = listPlaylists(user, page, page_size, query_obj, order)
	return "json", makeResponseSuccess({
		"playlists": playlists,
		"count": playlists_count,
		"page_count": (playlists_count - 1) // page_size + 1
		})

@app.route('/lists/get_playlist.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_get_playlist_do(rd, user, data):
	page_size = getDefaultJSON(data, 'page_size', 20)
	page = getDefaultJSON(data, 'page', 1) - 1
	lang = getDefaultJSON(data, 'lang', 'CHS')
	playlist = getPlaylist(data.pid, lang)
	if playlist["item"]["private"] and str(playlist["meta"]["created_by"]) != str(user['_id']) and user['access_control']['status'] != 'admin' :
		abort(404)
	playlist_editable = False
	if user:
		videos, video_count, playlist_editable = listPlaylistVideosWithAuthorizationInfo(data.pid, page, page_size, user)
	else:
		videos, video_count = listPlaylistVideos(data.pid, page, page_size, user)
	tags = playlist_db.retrive_item_with_tag_category_map(playlist['_id'], lang)
	return "json", makeResponseSuccess({
		"editable": playlist_editable,
		"playlist": playlist,
		"tags": tags,
		"videos": [item for item in videos],
		"count": video_count,
		"page_count": (video_count - 1) // page_size + 1
		})

@app.route('/lists/get_playlist_metadata.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_lists_get_playlist_metadata_do(rd, user, data):
	lang = getDefaultJSON(data, 'lang', 'CHS')
	playlist = getPlaylist(data.pid, lang)
	if playlist["item"]["private"] and str(playlist["meta"]["created_by"]) != str(user['_id']) :
		abort(404)
	tags = playlist_db.retrive_item_with_tag_category_map(playlist['_id'], lang)
	playlist_editable = False
	if user:
		playlist_editable = isAuthorised(playlist, user)
	return "json", makeResponseSuccess({
		"editable": playlist_editable,
		"tags": tags,
		"playlist": playlist
		})

@app.route('/lists/update_playlist_metadata.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_update_playlist_metadata_do(rd, user, data):
	privateEdit = getDefaultJSON(data, 'privateEdit', True)
	updatePlaylistInfo(data.pid, data.title, data.desc, None, user, data.private, data.privateEdit)

@app.route('/lists/del_playlist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_del_playlist_do(rd, user, data):
	removePlaylist(data.pid, user)

@app.route('/lists/create_from_copies.do', methods = ['POST']) # untested
@loginRequiredJSON
@jsonRequest
def ajax_lists_create_from_copies_do(rd, user, data):
	pid = createPlaylistFromCopies(data.pid, data.site, user)
	return "json", makeResponseSuccess(str(pid))

@app.route('/lists/create_from_video.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_create_from_video_do(rd, user, data):
	pid = createPlaylistFromSingleVideo(data.vid, user)
	return "json", makeResponseSuccess(str(pid))

@app.route('/lists/create_from_existing_playlists.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_create_from_existing_playlists(rd, user, data):
	new_playlist_id, task_id = createPlaylistFromExistingPlaylist(data.url, user, data.lang)
	return "json", makeResponseSuccess({'pid': str(new_playlist_id), 'task_id': task_id})

@app.route('/lists/extend_from_existing_playlists.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_extend_from_existing_playlists(rd, user, data):
	task_id = extendPlaylistFromExistingPlaylist(data.pid, data.url, user)
	return "json", makeResponseSuccess({'pid': str(data.pid), 'task_id': task_id})
