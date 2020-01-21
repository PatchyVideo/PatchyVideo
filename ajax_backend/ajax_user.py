
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, basePage, loginRequiredJSON
from utils.jsontools import *

from services.user import *
from config import UserConfig

@app.route('/auth/get_session.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_auth_get_session_do(rd, data):
	ret = require_session(data.type)
	return "json", makeResponseSuccess(ret)

@app.route('/login.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_login(rd, data):
	sid = login(data.username, data.password, '', data.session)
	session['sid'] = sid

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

@app.route('/user/profile.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_profile(rd, user, data):
	if data.uid == 'me' and user :
		return "json", makeResponseSuccess(user)
	obj = query_user(data.uid)
	return "json", makeResponseSuccess(obj)

@app.route('/user/profile_username.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_profile_username(rd, user, data):
	obj = queryUsername(data.username)
	return "json", makeResponseSuccess(obj)

@app.route('/user/changedesc.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changedesc(rd, user, data):
	update_desc(session['sid'], user['_id'], data.desc)

@app.route('/user/changephoto.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changephoto(rd, user, data):
	update_userphoto(session['sid'], user['_id'], data.file_key)

@app.route('/user/changeemail.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changeemail(rd, user, data):
	update_email(session['sid'], user['_id'], data.new_email)

@app.route('/user/changepass.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changepass(rd, user, data):
	update_password(user['_id'], data.old_pass, data.new_pass)

@app.route('/user/request_resetpass.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_request_resetpass(rd, user, data):
	request_password_reset(data.email, 'CHS')

@app.route('/user/resetpass.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_user_resetpass(rd, user, data):
	reset_password(data.reset_key, data.new_pass)

@app.route('/user/whoami', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_whoami(rd, user, data):
	return "json", makeResponseSuccess(whoAmI(user))

@app.route('/user/admin/updaterole.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_updaterole(rd, user, data):
	updateUserRole(user['_id'], data.role, user)

@app.route('/user/admin/updatemode.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_updatemode(rd, user, data):
	updateUserAccessMode(user['_id'], data.mode, user)

@app.route('/user/admin/get_allowedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_get_allowedops(rd, user, data):
	ret = getUserAllowedOps(user['_id'], user)
	return "json", makeResponseSuccess(ret)

@app.route('/user/admin/get_deniedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_get_get_deniedops(rd, user, data):
	ret = getUserDeniedOps(user['_id'], user)
	return "json", makeResponseSuccess(ret)

@app.route('/user/admin/update_allowedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_update_allowedops(rd, user, data):
	updateUserAllowedOps(user['_id'], data.ops, user)

@app.route('/user/admin/update_deniedops.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_update_deniedops(rd, user, data):
	updateUserDeniedOps(user['_id'], data.ops, user)
