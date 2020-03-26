
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from services.authorDB import createOrModifyAuthorRecord, getAuthorRecord
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



