
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
	note_type = getDefaultJSON(data, 'note_type', 'all')
	ans, count, count_unread, count_all = listMyNotificationUnread(user, note_type)
	return "json", makeResponseSuccess({'notes': ans, 'count': count, 'count_unread': count_unread, 'count_all': count_all})

@app.route('/notes/list_all.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_list_all(rd, user, data):
	offset, limit = getOffsetLimitJSON(data)
	note_type = getDefaultJSON(data, 'note_type', 'all')
	ans, count, count_unread, count_all = listMyNotificationAll(user, offset, limit, note_type)
	return "json", makeResponseSuccess({'notes': ans, 'count': count, 'count_unread': count_unread, 'count_all': count_all, "page_count": (count - 1) // limit + 1})

@app.route('/notes/unread_count.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_unread_count(rd, user, data):
	note_type = getDefaultJSON(data, 'note_type', 'all')
	return "json", makeResponseSuccess(getUnreadNotificationCount(user, note_type))

@app.route('/notes/mark_read.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_mark_read(rd, user, data):
	markRead(user, data.note_ids)

@app.route('/notes/mark_all_read.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_mark_all_read(rd, user, data):
	note_type = getDefaultJSON(data, 'note_type', 'all')
	markAllRead(user, note_type)

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
