
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from services.subtitles import listVideoSubtitles, getSubtitle, postSubtitle, requireSubtitleOCR
from services.tcb import filterOperation

from bson import ObjectId

@app.route('/subtitles/list_for_video.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_subtitles_list_for_video(rd, user, data):
	items = listVideoSubtitles(ObjectId(data.vid))
	return "json", makeResponseSuccess({'items': items})

@app.route('/subtitles/get_single.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_subtitles_get_single(rd, user, data):
	item = getSubtitle(ObjectId(data.subid))
	return "json", makeResponseSuccess({'item': item})

@app.route('/subtitles/post_subtitle.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_post_subtitle(rd, user, data):
	subid = postSubtitle(user, ObjectId(data.vid), data.lang, data.format, data.content)
	return "json", makeResponseSuccess({'subid': subid})

