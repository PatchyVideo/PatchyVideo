
import time

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from services.playlist import *
from utils.html import buildPageSelector

@app.route('/list/getcommontags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_playlist_getcommontags_do(rd, data, user):
    ret, tags = listCommonTags(data.pid)
    if ret == 'SUCCEED' :
        return "json", makeResponseSuccess(tags)
    else :
        return "json", makeResponseFailed(ret)

@app.route('/list/setcommontags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_setcommontags_do(rd, user, data):
    ret = updateCommonTags(data.pid, data.tags, user)
    if ret == 'SUCCEED' :
        return "json", makeResponseSuccess('')
    else :
        return "json", makeResponseFailed(ret)

@app.route('/list/setcover.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_setcover_do(rd, user, data):
    ret, new_list = updatePlaylistCoverVID(data.pid, data.vid, int(data.page), int(data.page_size), user)
    if ret == 'SUCCEED' :
        return "json", makeResponseSuccess(new_list)
    else :
        return "json", makeResponseFailed(ret)

@app.route('/list/delete.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_deletevideo_do(rd, user, data):
    ret, new_list = removeVideoFromPlaylist(data.pid, data.vid, int(data.page), int(data.page_size), user)
    if ret == 'SUCCEED' :
        return "json", makeResponseSuccess(new_list)
    else :
        return "json", makeResponseFailed(ret)

@app.route('/list/moveup.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_moveup_do(rd, user, data):
    ret, new_list = editPlaylist_MoveUp(data.pid, data.vid, int(data.page), int(data.page_size), user)
    if ret == 'SUCCEED' :
        return "json", makeResponseSuccess(new_list)
    else :
        return "json", makeResponseFailed(ret)

@app.route('/list/movedown.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_playlist_movedown_do(rd, user, data):
    ret, new_list = editPlaylist_MoveDown(data.pid, data.vid, int(data.page), int(data.page_size), user)
    if ret == 'SUCCEED' :
        return "json", makeResponseSuccess(new_list)
    else :
        return "json", makeResponseFailed(ret)

@app.route('/lists/new.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_lists_new_do(rd, user, data):
    if len(data.title) > PlaylistConfig.MAX_TITLE_LENGTH or len(data.desc) > PlaylistConfig.MAX_DESC_LENGTH or len(data.cover) > PlaylistConfig.MAX_COVER_URL_LENGTH :
        return "json", makeResponseFailed("Data too large(max 128 chars for title, 2048 for description)")
    if not data.title or not data.desc :
        return "json", makeResponseFailed("Please fill all items")
    if data.pid :
        result = updatePlaylistInfo(data.pid, "english", data.title, data.desc, data.cover, user)
        if result == 'SUCCEED' :
            pid = data.pid
        else :
            return "json", result
    else :
        pid = createPlaylist("english", data.title, data.desc, data.cover, user)
    ret = makeResponseSuccess({
        "pid": pid
    })
    return "json", ret

