
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON, getOffsetLimitJSON

from services.notifications import listMyNotificationUnread, listMyNotificationAll, getUnreadNotificationCount, markRead, markAllRead
from services.tcb import filterOperation

from bson import ObjectId

@app.route('/notes/list_unread.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_list_unread(rd, user, data):
	ans = listMyNotificationUnread(user)
	return "json", makeResponseSuccess({'notes': ans})

@app.route('/notes/list_all.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_notes_list_all(rd, user, data):
	offset, limit = getOffsetLimitJSON(data)
	ans = listMyNotificationAll(user, offset, limit)
	return "json", makeResponseSuccess({'notes': ans})

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
