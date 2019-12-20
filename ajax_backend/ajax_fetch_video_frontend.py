import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.logger import log

from spiders import dispatch
from spiders.Twitter import Twitter

@app.route('/helper/get_twitter_info.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_helper_get_twitter_info(rd, user, data):
	log(obj = {'url': data.url})
	obj, cleanURL = dispatch(data.url)
	if obj.NAME != 'twitter' :
		log(obj = {'msg': 'NOT_TWITTER'})
		return makeResponseFailed('NOT_TWITTER')
	info = obj.get_metadata(obj, cleanURL)
	if info["status"] != 'SUCCEED' :
		log(obj = {'msg': 'FETCH_FAILED', 'info': info})
		return makeResponseFailed('FETCH_FAILED')
	return info

@app.route('/helper/get_ytb_info.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_helper_get_ytb_info(rd, user, data):
	log(obj = {'url': data.url})
	obj, cleanURL = dispatch(data.url)
	if obj.NAME != 'youtube' :
		log(obj = {'msg': 'NOT_YOUTUBE'})
		return makeResponseFailed('NOT_YOUTUBE')
	info = obj.get_metadata(obj, cleanURL)
	if info["status"] != 'SUCCEED' :
		log(obj = {'msg': 'FETCH_FAILED', 'info': info})
		return makeResponseFailed('FETCH_FAILED')
	return info
