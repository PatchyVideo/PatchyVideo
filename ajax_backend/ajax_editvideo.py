import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from services.editVideo import editVideoTags, getVideoTags, refreshVideoDetail, refreshVideoDetailURL
from services.tcb import setVideoClearence
from config import TagsConfig, VideoConfig

@app.route('/videos/edittags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_edittags(rd, user, data):
	editVideoTags(data.video_id, data.tags, user)

@app.route('/videos/gettags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_videos_gettags(rd, user, data):
	tags = getVideoTags(data.video_id, 'CHS', user)
	return "json", makeResponseSuccess(tags)

@app.route('/videos/refresh.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_refresh(rd, user, data):
	refreshVideoDetail(data.video_id, user)

@app.route('/videos/refresh_url.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_refresh_url(rd, user, data):
	refreshVideoDetailURL(data.url, user)

@app.route('/videos/set_clearence.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_set_clearence(rd, user, data):
	setVideoClearence(data.vid, data.clearence, user)
