
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from services.comment import addToVideo, addToPlaylist, addToUser, addComment, addReply, listThread, hideComment, delComment, editComment, pinComment
from services.tcb import filterOperation

from bson import ObjectId

@app.route('/comments/add_to_video.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_add_to_video(rd, user, data):
	thread_id, cid = addToVideo(user, ObjectId(data.vid), data.text)
	return "json", makeResponseSuccess({'thread_id': str(thread_id), 'cid': cid})

@app.route('/comments/add_to_playlist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_add_to_playlist(rd, user, data):
	thread_id, cid = addToPlaylist(user, ObjectId(data.pid), data.text)
	return "json", makeResponseSuccess({'thread_id': str(thread_id), 'cid': cid})

@app.route('/comments/add_to_user.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_add_to_user(rd, user, data):
	thread_id, cid = addToUser(user, ObjectId(data.uid), data.text)
	return "json", makeResponseSuccess({'thread_id': str(thread_id), 'cid': cid})

@app.route('/comments/reply.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_reply(rd, user, data):
	addReply(user, ObjectId(data.reply_to), data.text)

@app.route('/comments/hide.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_hide(rd, user, data):
	hideComment(user, ObjectId(data.cid))

@app.route('/comments/del.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_del(rd, user, data):
	delComment(user, ObjectId(data.cid))

@app.route('/comments/edit.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_edit(rd, user, data):
	editComment(user, data.text, ObjectId(data.cid))

@app.route('/comments/pin.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_pin(rd, user, data):
	pinComment(user, ObjectId(data.cid), data.pinned)

@app.route('/comments/view.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_comments_view(rd, user, data):
	comments, users = listThread(ObjectId(data.thread_id))
	return "json", makeResponseSuccess({'comments': comments, 'users': users})
