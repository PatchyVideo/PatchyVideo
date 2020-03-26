
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from services.copies import breakLink, syncTags, broadcastTags

@app.route('/videos/breaklink.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_breaklink(rd, user, data):
	breakLink(data.video_id, user)

@app.route('/videos/synctags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_synctags(rd, user, data):
	syncTags(data.dst, data.src, user)

@app.route('/videos/broadcasttags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_broadcasttags(rd, user, data):
	broadcastTags(data.src, user)
