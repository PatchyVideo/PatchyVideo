
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from services.tagStatistics import getRelatedTagsExperimental
from services.autotag import inferTagsFromUtags

@app.route('/tags/get_related_tags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_get_related_tags_do(rd, user, data):
	max_count = data.max_count if 'max_count' in data.__dict__ and data.max_count is not None else 10
	start = time.time()
	ret = getRelatedTagsExperimental('CHS', data.tags, max_count)
	end = time.time()
	return "json", makeResponseSuccess({'tags': ret, 'time_used_ms': int((end - start) * 1000)})

@app.route('/tags/autotag.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_autotag_do(rd, user, data) :
	tags = inferTagsFromUtags(data.utags, 'CHS')
	return "json", makeResponseSuccess({'tags': tags})
