
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON, getOffsetLimitJSON

from services.notifications import listMyNotificationUnread, listMyNotificationAll, getUnreadNotificationCount, markRead, markAllRead, broadcastNotificationWithContent, createDirectMessage
from services.tcb import filterOperation

from bson import ObjectId

@app.route('/notes/list_unread.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_list_unread(rd, user, data):
	ans, count = listMyNotificationUnread(user)
	return "json", makeResponseSuccess({'notes': ans, 'count': count})

@app.route('/notes/list_all.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_list_all(rd, user, data):
	offset, limit = getOffsetLimitJSON(data)
	ans, count = listMyNotificationAll(user, offset, limit)
	return "json", makeResponseSuccess({'notes': ans, 'count': count})

@app.route('/notes/unread_count.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_unread_count(rd, user, data):
	return "json", makeResponseSuccess(getUnreadNotificationCount(user))

@app.route('/notes/mark_read.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_mark_read(rd, user, data):
	markRead(user, data.note_ids)

@app.route('/notes/mark_all_read.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_mark_all_read(rd, user, data):
	markAllRead(user)

@app.route('/notes/admin/broadcast.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_admin_broadcast(rd, user, data):
	filterOperation('broadcastNotification', user)
	broadcastNotificationWithContent(data.content)

@app.route('/notes/send_dm.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_send_dm(rd, user, data):
	filterOperation('sendDM', user)
	if len(data.content) > 65536 :
		raise UserError('CONTENT_TOO_LONG')
	createDirectMessage(user['_id'], ObjectId(data.dst_user), other = {'content': data.content})
