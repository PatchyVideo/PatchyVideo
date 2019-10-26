import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch
from spiders.Twitter import Twitter

@app.route('/helper/get_twitter_infxo.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_helper_get_twitter_info(rd, user, data):
    obj, cleanURL = dispatch(data.url)
    if obj.NAME != 'twitter' :
        return makeResponseFailed('Not twitter')
    info = obj.get_metadata(obj, cleanURL)
    if info["status"] != 'success' :
        return makeResponseFailed('Failed to fetch twitter info')
    return info
