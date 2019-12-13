
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, basePage, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.user import *
from config import UserConfig

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

@app.route('/user/changedesc.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changedesc(rd, user, data):
	update_desc(session['sid'], user['_id'], data.desc)

@app.route('/user/changepass.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_user_changepass(rd, user, data):
	update_password(user['_id'], data.old_pass, data.new_pass)

