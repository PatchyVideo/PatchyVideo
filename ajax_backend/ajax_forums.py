
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from services.forums import postThreadToForum, viewSingleForumThread, listForumThreads, addToThread, addReplyToThread, deleteThread, pinThread

from bson import ObjectId

@app.route('/forums/post_thread.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_forums_post_thread(rd, user, data):
	ftid = postThreadToForum(user, ObjectId(data.forum_id), data.title, data.text)
	return "json", makeResponseSuccess({'forum_tid': ftid})

@app.route('/forums/view_thread.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_forums_view_thread(rd, user, data):
	comments, users, title = viewSingleForumThread(ObjectId(data.forum_tid))
	return "json", makeResponseSuccess({'comments': comments, 'users': users, 'title': title})

@app.route('/forums/delete_thread.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_forums_delete(rd, user, data):
	deleteThread(user, ObjectId(data.forum_tid))

@app.route('/forums/pin_thread.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_forums_pin(rd, user, data):
	pinThread(user, ObjectId(data.forum_tid), data.pinned)

@app.route('/forums/view_forum.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_forums_view_forum(rd, user, data):
	page_idx = getDefaultJSON(data, 'page', 1) - 1
	page_size = getDefaultJSON(data, 'page_size', 30)
	threads = listForumThreads(ObjectId(data.forum_id), page_idx, page_size)
	return "json", makeResponseSuccess({'threads': threads})

@app.route('/forums/add_to_thread.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_forums_add_to_thread(rd, user, data):
	cid = addToThread(user, ObjectId(data.forum_tid), data.text)
	return "json", makeResponseSuccess({'cid': cid})

@app.route('/forums/reply.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_forums_reply(rd, user, data):
	addReplyToThread(user, ObjectId(data.reply_to), data.text)
