
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from services.subtitles import *
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

@app.route('/subtitles/get_single_translated.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_subtitles_get_single_translated(rd, user, data):
	text = translateVTT(ObjectId(data.subid), data.lang)
	return "json", makeResponseSuccess(text)

@app.route('/subtitles/post_subtitle.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_post_subtitle(rd, user, data):
	subid = postSubtitle(user, ObjectId(data.vid), data.lang, data.format, data.content)
	return "json", makeResponseSuccess({'subid': subid})

@app.route('/subtitles/update_subtitle_meta.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_update_subtitle_meta(rd, user, data):
	updateSubtitleMeta(user, ObjectId(data.subid), data.lang, data.format)

@app.route('/subtitles/update_subtitle_content.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_update_subtitle_content(rd, user, data):
	updateSubtitleContent(user, ObjectId(data.subid), data.content)

@app.route('/subtitles/delete_subtitle.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_delete_subtitle(rd, user, data):
	deleteSubtitle(user, ObjectId(data.subid))

@app.route('/subtitles/request_ocr.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_request_ocr(rd, user, data):
	requestSubtitleOCR(user, ObjectId(data.vid))

@app.route('/subtitles/query_ocr_status.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_subtitles_query_ocr_status(rd, user, data):
	status = querySubtitleOCRStatus(ObjectId(data.vid))
	return "json", makeResponseSuccess({'status': status})

@app.route('/subtitles/worker/query_queue.do', methods = ['POST'])
@loginRequiredJSON # use a dedicated account
@jsonRequest
def ajax_subtitles_worker_query_queue(rd, user, data):
	video_urls = queryAndProcessQueuingRequests(user, int(data.max_videos), data.worker_id)
	return "json", makeResponseSuccess({'urls': video_urls})

@app.route('/subtitles/worker/update_status.do', methods = ['POST'])
@loginRequiredJSON # use a dedicated account
@jsonRequest
def ajax_subtitles_worker_update_status(rd, user, data):
	updateRequestStatus(user, data.unique_id_status_map, data.worker_id)

@app.route('/subtitles/worker/post_ocr_result.do', methods = ['POST'])
@loginRequiredJSON # use a dedicated account
@jsonRequest
def ajax_subtitles_worker_post_ocr_result(rd, user, data):
	subid = postSubtitleOCRResult(user, data.unique_id, data.content, data.format, int(data.version), data.worker_id)
	return "json", makeResponseSuccess({'subid': subid})

@app.route('/subtitles/admin/list_pending_ocr_requests.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_admin_list_pending_ocr_requests(rd, user, data):
	order = getDefaultJSON(data, 'order', 'oldest')
	page_idx = getDefaultJSON(data, 'page', 1) - 1
	page_size = getDefaultJSON(data, 'page_size', 30)
	result, count = listAllPendingRequest(user, order, page_idx, page_size)
	return "json", makeResponseSuccess({'items': result, 'total': count})

@app.route('/subtitles/admin/set_request_status.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_admin_set_request_status(rd, user, data):
	setRequestStatus(user, ObjectId(data.vid), data.status)

@app.route('/subtitles/admin/set_all_request_status.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_subtitles_admin_set_all_request_status(rd, user, data):
	setAllRequestStatus(user, data.status)
