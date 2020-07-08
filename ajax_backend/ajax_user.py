
import time

import redis
import base64
import urllib

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, basePage, loginRequiredJSON, loginOptionalGET
from utils.jsontools import *

from services.user import *
from config import UserConfig
import urllib.parse

@app.route('/auth/get_session.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_auth_get_session_do(rd, data):
	ret = require_session(data.type)
	return "json", makeResponseSuccess(ret)

@app.route('/auth/callback', methods = ['GET'])
@loginOptionalGET
def ajax_auth_callback(rd, user, data):
	# TODO: verify request is from QQ
	od = data['param']['code'].replace('-', '+').replace(',', '=').replace('_', '/')
	b64 = base64.b64decode(od)
	code = urllib.parse.parse_qs(b64.decode('utf-8'))
	nickname = code['nickname'][0]
	openid = code['openid'][0]
	atype = data['param']['type']
	if atype != 'qq' :
		raise UserError('NOT_QQ')
	if user is not None :
		bind_qq_openid(user, openid)
		return "redirect", "https://thvideo.tv/#/?bind_qq_openid=succeed"
	succeed, sid = login_auth_qq(openid, nickname)
	if succeed :
		session['sid'] = sid
		return "redirect", "https://thvideo.tv/"
	else :
		return "redirect", "https://thvideo.tv/#/login?session=%s&nickname=%s" % (sid, urllib.parse.quote(nickname))

@app.route('/login.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_login(rd, data):
	sid, obj = login(data.username, data.password, '', data.session)
	session['sid'] = sid
	return "json", makeResponseSuccess(obj)

@app.route('/logout.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_logout(rd, user, data) :
    if user is not None:
        logout(session['sid'])
        session.pop('sid', None)

@app.route('/auth/unbind_qq.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_unbind_qq(rd, user, data) :
    unbind_qq(user)

@app.route('/signup.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_signup(rd, data):
	uid = signup(data.username, data.password, data.email, '', data.session)
	return "json", makeResponseSuccess({'uid': str(uid)})

@app.route('/user/exists.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_user_exists(rd, data):
	return "json", makeResponseSuccess(checkIfUserExists(data.username))

@app.route('/user/myprofile.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_myprofile(rd, user, data):
	return "json", makeResponseSuccess(user)

@app.route('/user/view_opinion.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_view_opinion(rd, user, data):
	thread, users = viewOpinion(user)
	return "json", makeResponseSuccess({'comments': thread, 'users': users})

@app.route('/user/profile.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_profile(rd, user, data):
	if data.uid == 'me' and user :
		return "json", makeResponseSuccess(user)
	obj = query_user(data.uid)
	return "json", makeResponseSuccess(obj)

@app.route('/user/profile_batch.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_profile_batch(rd, user, data):
	obj = query_user_batch(data.uids)
	return "json", makeResponseSuccess(obj)

@app.route('/user/profile_username.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_profile_username(rd, user, data):
	obj = queryUsername(data.username)
	return "json", makeResponseSuccess(obj)

@app.route('/user/get_blacklist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_get_blacklist(rd, user, data):
	return "json", makeResponseSuccess(queryBlacklist(user, data.lang))

@app.route('/user/changedesc.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changedesc(rd, user, data):
	update_desc(session['sid'], user['_id'], data.desc)

@app.route('/user/changename.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changename(rd, user, data):
	update_username(session['sid'], user['_id'], data.name)

@app.route('/user/changephoto.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changephoto(rd, user, data):
	photo_file = update_userphoto(session['sid'], user['_id'], data.file_key)
	return "json", makeResponseSuccess(photo_file)

@app.route('/user/changeemail.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changeemail(rd, user, data):
	update_email(session['sid'], user['_id'], data.new_email)

@app.route('/user/changeblacklist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changeblacklist(rd, user, data):
	update_blacklist(session['sid'], user['_id'], data.blacklist)

@app.route('/user/changepass.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changepass(rd, user, data):
	update_password(user['_id'], data.old_pass, data.new_pass)

@app.route('/user/request_resetpass.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_request_resetpass(rd, user, data):
	request_password_reset(data.email, data.lang)

@app.route('/user/resetpass.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_resetpass(rd, user, data):
	reset_password(data.reset_key, data.new_pass)

@app.route('/user/whoami', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_whoami(rd, user, data):
	if not user :
		return "json", makeResponseError("UNAUTHORISED_OPERATION")
	return "json", makeResponseSuccess(whoAmI(user))

@app.route('/user/is_authorized', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_is_authorized(rd, user, data):
	checkIsAuthorized(user, data.op)

@app.route('/user/admin/updaterole.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_updaterole(rd, user, data):
	updateUserRole(data.uid, data.role, user)

@app.route('/user/admin/updatemode.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_updatemode(rd, user, data):
	updateUserAccessMode(data.uid, data.mode, user)

@app.route('/user/admin/get_allowedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_get_allowedops(rd, user, data):
	ret = getUserAllowedOps(data.uid, user)
	return "json", makeResponseSuccess(ret)

@app.route('/user/admin/get_deniedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_get_get_deniedops(rd, user, data):
	ret = getUserDeniedOps(data.uid, user)
	return "json", makeResponseSuccess(ret)

@app.route('/user/admin/update_allowedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_update_allowedops(rd, user, data):
	updateUserAllowedOps(data.uid, data.ops, user)

@app.route('/user/admin/update_deniedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_update_deniedops(rd, user, data):
	updateUserDeniedOps(data.uid, data.ops, user)

@app.route('/user/list_users.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_list_users(rd, user, data):
	page_idx = getDefaultJSON(data, 'page', 1) - 1
	page_size = getDefaultJSON(data, 'page_size', 20)
	query = getDefaultJSON(data, 'query', '')
	order = getDefaultJSON(data, 'order', 'latest')
	users, count = listUsers(user, page_idx, page_size, query, order)
	ret = makeResponseSuccess({
		"users": users,
		"count": count,
		"page_count": (count - 1) // page_size + 1
	})
	return "json", ret


