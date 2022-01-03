import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from services.editVideo import editVideoTags, getVideoTags, refreshVideoDetail, refreshVideoDetailURL, editVideoTagsQuery, setVideoRepostType
from services.tcb import setVideoClearence
from config import TagsConfig, VideoConfig

@app.route('/videos/edittags.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_edittags(rd, user, data):
	user_lang = getDefaultJSON(data, 'user_language', 'ENG')
	edit_behaviour = getDefaultJSON(data, 'edit_behaviour', 'replace')
	not_found_behaviour = getDefaultJSON(data, 'not_found_behaviour', 'ignore')
	new_tagids = editVideoTags(data.video_id, data.tags, user, edit_behaviour, not_found_behaviour, user_lang)
	return "json", makeResponseSuccess({'tagids': new_tagids})

@app.route('/videos/edittagids.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_edittags(rd, user, data):
	user_lang = getDefaultJSON(data, 'user_language', 'ENG')
	edit_behaviour = getDefaultJSON(data, 'edit_behaviour', 'replace')
	not_found_behaviour = getDefaultJSON(data, 'not_found_behaviour', 'ignore')
	new_tagids = editVideoTags(data.video_id, [int(item) & 0x7fffffff for item in data.tags], user, edit_behaviour, not_found_behaviour, user_lang, is_tagids = True)
	return "json", makeResponseSuccess({'tagids': new_tagids})

@app.route('/videos/edittags_batch.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_edittags_batch(rd, user, data):
	query_type = getDefaultJSON(data, 'query_type', 'tag')
	count = editVideoTagsQuery(data.query, query_type, data.tags_add, data.tags_del, user)
	return makeResponseSuccess(count)

@app.route('/videos/gettags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_videos_gettags(rd, user, data):
	tags = getVideoTags(data.video_id, data.lang, user)
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
	clearence = getDefaultJSON(data, 'clearence', 0)
	setVideoClearence(data.vid, clearence, user)
	return "json", makeResponseSuccess({'clearence': clearence})

@app.route('/videos/condemn_video.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_condemn_video(rd, user, data):
	setVideoClearence(data.vid, 0, user)
	editVideoTags(data.vid, [], user, 'replace', 'ignore', 'CHS')
	return "json", makeResponseSuccess({})

@app.route('/videos/set_repost_type.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_videos_set_repost_type(rd, user, data):
	setVideoRepostType(data.vid, data.repost_type, user)
