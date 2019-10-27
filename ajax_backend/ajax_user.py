
import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, basePage, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.user import *

@app.route('/login.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_login(rd, data):
    if len(data.username) > 32 or len(data.username) < 4:
        return "json", makeResponseFailed("Username length not satisfied")
    if len(data.password) > 64 or len(data.password) < 8:
        return "json", makeResponseFailed("Password length not satisfied")
    result, sid = login(data.username, data.password, '', data.session)
    if result == 'SUCCEED' :
        ret = makeResponseSuccess({})
        session['sid'] = sid
    else :
        ret = makeResponseFailed(result)
    return "json", ret

@app.route('/signup.do', methods = ['POST'])
@basePage
@jsonRequest
def ajax_signup(rd, data):
    if len(data.username) > 14 or len(data.username) < 3:
        return "json", makeResponseFailed("Username length not satisfied")
    if len(data.password) > 64 or len(data.password) < 8:
        return "json", makeResponseFailed("Password length not satisfied")
    result, uid = signup(data.username, data.password, data.email, '', data.session)
    if result == 'SUCCEED' :
        ret = makeResponseSuccess({'uid': str(uid)})
    else :
        ret = makeResponseFailed(result)
    return "json", ret

@app.route('/user/changedesc.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changedesc(rd, user, data):
    result = update_desc(session['sid'], user['_id'], data.desc)
    if result == 'SUCCEED' :
        ret = makeResponseSuccess({})
    elif result == 'DESC_LENGTH' :
        ret = makeResponseFailed('Description too long(max 2000 characters)')
    else :
        ret = makeResponseFailed(result)
    return "json", ret

@app.route('/user/changepass.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changepass(rd, user, data):
    result = update_password(user['_id'], data.old_pass, data.new_pass)
    if result == 'SUCCEED' :
        ret = makeResponseSuccess({})
    elif result == 'INCORRECT_PASSWORD' :
        ret = makeResponseFailed('Incorrect password')
    elif result == 'PASSWORD_LENGTH' :
        ret = makeResponseFailed('Password length must be between 8 and 64 characters long')
    else :
        ret = makeResponseFailed(result)
    return "json", ret

