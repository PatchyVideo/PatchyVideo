
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON, getOffsetLimitJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError
from services.tcb import filterOperation

from services.logViewer import viewLogs, viewLogsAggregated, viewRawTagHistoryRetId, viewTaghistory, viewRawTagHistory

from dateutil.parser import parse
from datetime import timezone

@app.route('/admin/viewlogs.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_admin_viewlogs_do(rd, data, user):
	filterOperation('viewlogs', user)
	order = getDefaultJSON(data, 'order', 'latest')
	date_from = getDefaultJSON(data, 'date_from', '')
	date_to = getDefaultJSON(data, 'date_to', '')
	offset, limit = getOffsetLimitJSON(data)
	levels = getDefaultJSON(data, 'levels', ['SEC', 'MSG', 'WARN', 'ERR'])
	op = getDefaultJSON(data, 'op', '')
	if date_from :
		date_from = parse(date_from).astimezone(timezone.utc)
	if date_to :
		date_to = parse(date_to).astimezone(timezone.utc)
	ret = viewLogs(offset, limit, date_from, date_to, order, op, levels)
	return "json", makeResponseSuccess(ret)

@app.route('/admin/viewlogs_aggregated.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_admin_viewlogs_aggregated_do(rd, data, user):
	filterOperation('viewlogs', user)
	order = getDefaultJSON(data, 'order', 'latest')
	date_from = getDefaultJSON(data, 'date_from', '')
	date_to = getDefaultJSON(data, 'date_to', '')
	offset, limit = getOffsetLimitJSON(data)
	levels = getDefaultJSON(data, 'levels', ['SEC', 'MSG', 'WARN', 'ERR'])
	op = getDefaultJSON(data, 'op', '')
	if date_from :
		date_from = parse(date_from).astimezone(timezone.utc)
	if date_to :
		date_to = parse(date_to).astimezone(timezone.utc)
	ret = viewLogsAggregated(offset, limit, date_from, date_to, order, op, levels)
	return "json", makeResponseSuccess(ret)

@app.route('/video/tag_log.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_video_tag_log_do(rd, data, user):
	return "json", makeResponseSuccess(viewTaghistory(data.vid, data.lang))

@app.route('/video/raw_tag_log.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_video_raw_tag_log_do(rd, data, user):
	offset, limit = getOffsetLimitJSON(data)
	return "json", makeResponseSuccess(viewRawTagHistory(offset, limit, data.lang))

@app.route('/video/raw_tagid_log.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_video_raw_tagid_log_do(rd, data, user):
	offset, limit = getOffsetLimitJSON(data)
	return "json", makeResponseSuccess({'items': viewRawTagHistoryRetId(offset, limit)})
