
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError

from services.config import Config
from services.tcb import filterOperation

@app.route('/config/setconfig.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_config_setconfig(rd, user, data):
	filterOperation('setConfig', user, data.attr)
	Config.__setattr__(data.attr, data.data)

@app.route('/config/getconfig.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_config_getconfig(rd, user, data):
	filterOperation('getConfig', user, data.attr)
	return makeResponseSuccess(Config.__getattr__(data.attr))

@app.route('/config/listconfig.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_config_listconfig(rd, user, data):
	filterOperation('listConfig', user, data.attr)
	return makeResponseSuccess(Config.ListAttrs())

