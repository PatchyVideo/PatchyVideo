
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from bson import ObjectId

from services.authorDB import associateWithPvUser, createOrModifyAuthorRecord, disassociateWithPvUser, findTagByUser, getAuthorRecord, getAuthorRecordTranslationFree
from services.tcb import filterOperation

@app.route('/authors/create_or_modify.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_authors_create_or_modify(rd, user, data):
	filekey = getDefaultJSON(data, 'avatar_file_key', '')
	record_id = createOrModifyAuthorRecord(user,
		data.author_type,
		data.tagid,
		data.common_tags,
		data.user_spaces,
		data.desc,
		filekey
		)
	return "json", makeResponseSuccess({'record_id': record_id})

@app.route('/authors/get_record.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_authors_get_record(rd, user, data):
	return "json", makeResponseSuccess({"record": getAuthorRecord(data.tag, data.lang)})

@app.route('/authors/get_record_raw.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_authors_get_record_raw(rd, user, data):
	return "json", makeResponseSuccess({"record": getAuthorRecordTranslationFree(int(data.tagid))})

@app.route('/authors/associate_with_pv_user.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_authors_associate_with_pv_user(rd, user, data):
	associateWithPvUser(user, data.tagid, ObjectId(data.uid))

@app.route('/authors/disassociate_with_pv_user.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_authors_disassociate_with_pv_user(rd, user, data):
	disassociateWithPvUser(user, data.tagid, ObjectId(data.uid))


# @app.route('/authors/find_tag_by_pv_uid.do', methods = ['POST'])
# @loginOptional
# @jsonRequest
# def ajax_authors_find_tag_by_pv_uid(rd, user, data):
# 	return "json", makeResponseSuccess(findTagByUser(ObjectId(data.uid)))




