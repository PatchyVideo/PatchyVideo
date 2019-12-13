
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from services.tagStatistics import getRelatedTagsExperimental

@app.route('/tags/get_related_tags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_get_related_tags_do(rd, user, data):
	max_count = data.max_count if 'max_count' in data.__dict__ and data.max_count is not None else 10
	ret = getRelatedTagsExperimental('CHS', data.tags, max_count)
	return "json", makeResponseSuccess(ret)

