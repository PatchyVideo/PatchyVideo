
import time

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from services.playlist import *
from utils.html import buildPageSelector


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
