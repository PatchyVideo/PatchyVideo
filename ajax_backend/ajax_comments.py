
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from services.comment import addToVideo, addToPlaylist, addToUser, addComment, addReply, listThread
from services.tcb import filterOperation

from bson import ObjectId

@app.route('/comments/add_to_video.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_add_to_video(rd, user, data):
	thread_id = addToVideo(user, ObjectId(data.vid), data.text)
	return "json", makeResponseSuccess({'thread_id': thread_id})

@app.route('/comments/add_to_playlist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_add_to_playlist(rd, user, data):
	thread_id = addToPlaylist(user, ObjectId(data.pid), data.text)
	return "json", makeResponseSuccess({'thread_id': thread_id})

@app.route('/comments/add_to_user.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_add_to_user(rd, user, data):
	thread_id = addToUser(user, ObjectId(data.uid), data.text)
	return "json", makeResponseSuccess({'thread_id': thread_id})

@app.route('/comments/reply.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_comments_reply(rd, user, data):
	addReply(user, ObjectId(data.reply_to), data.text)

@app.route('/comments/view.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_comments_view(rd, user, data):
	comments, users = listThread(ObjectId(data.thread_id))
	return "json", makeResponseSuccess({'comments': comments, 'users': users})
