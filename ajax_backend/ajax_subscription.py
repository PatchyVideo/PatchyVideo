
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError
from services.tcb import filterOperation

from services.subscription import listSubscriptions, listSubscriptionTags, addSubscription, removeSubScription, updateSubScription, listSubscriptedItems, listSubscriptedItemsRandomized

from dateutil.parser import parse
from datetime import timezone

@app.route('/subs/add.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subs_add_do(rd, data, user):
	filterOperation('addSubs', user)
	qtype = getDefaultJSON(data, 'qtype', 'tag')
	name = getDefaultJSON(data, 'name', '')
	subid = addSubscription(user, data.query, qtype, name)
	return "json", makeResponseSuccess({'subid': subid})

@app.route('/subs/del.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subs_del_do(rd, data, user):
	filterOperation('delSubs', user)
	removeSubScription(user, data.subid)

@app.route('/subs/all.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subs_all_do(rd, data, user):
	subs = listSubscriptions(user)
	return "json", makeResponseSuccess({'subs': subs})

@app.route('/subs/tags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subs_tags_do(rd, data, user):
	items = listSubscriptionTags(user)
	return "json", makeResponseSuccess({'tagids': [i['tagid'] for i in items]})

@app.route('/subs/update.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subs_update_do(rd, data, user):
	filterOperation('updateSubs', user)
	qtype = getDefaultJSON(data, 'qtype', '')
	name = getDefaultJSON(data, 'name', '')
	updateSubScription(user, data.subid, data.query, qtype, name)

@app.route('/subs/list.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subs_list_do(rd, data, user):
	order = getDefaultJSON(data, 'order', 'video_latest')
	hide_placeholder = getDefaultJSON(data, 'hide_placeholder', True)
	lang = getDefaultJSON(data, 'lang', 'CHS')
	visible = getDefaultJSON(data, 'visible', [''])
	additional_constraint = getDefaultJSON(data, 'additional_constraint', '')
	if order not in ['latest', 'oldest', 'video_latest', 'video_oldest'] :
		raise AttributeError()
	videos, sub_objs, tags, count = listSubscriptedItems(
		user,
		data.page - 1,
		data.page_size,
		lang,
		hide_placeholder,
		order,
		visible,
		additional_constraint
		)
	return "json", makeResponseSuccess({
		'videos': videos,
		'objs': sub_objs,
		'related_tags': tags,
		'total': count
		})

@app.route('/subs/list_randomized.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subs_list_randomized_do(rd, data, user):
	lang = getDefaultJSON(data, 'lang', 'CHS')
	visible = getDefaultJSON(data, 'visible', [''])
	additional_constraint = getDefaultJSON(data, 'additional_constraint', '')
	videos, sub_objs, tags = listSubscriptedItemsRandomized(
		user,
		data.page_size,
		lang,
		visible,
		additional_constraint
		)
	return "json", makeResponseSuccess({
		'videos': videos,
		'objs': sub_objs,
		'related_tags': tags
		})
