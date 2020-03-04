
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from services.tagStatistics import getRelatedTagsExperimental
from services.autotag import inferTagsFromVideo
from services.editTag import getTag, getDefaultBlacklist

@app.route('/tags/get_related_tags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_get_related_tags_do(rd, user, data):
	max_count = getDefaultJSON(data, 'max_count', 10)
	exclude = getDefaultJSON(data, 'exclude', [])
	start = time.time()
	ret = getRelatedTagsExperimental(data.lang, data.tags, exclude, max_count)
	end = time.time()
	return "json", makeResponseSuccess({'tags': ret, 'time_used_ms': int((end - start) * 1000)})

@app.route('/tags/autotag.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_autotag_do(rd, user, data) :
	title = getDefaultJSON(data, 'title', '')
	desc = getDefaultJSON(data, 'desc', '')
	tags = inferTagsFromVideo(data.utags, title, desc, data.lang)
	return "json", makeResponseSuccess({'tags': tags})

@app.route('/tags/get_tag.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_tags_get_tag_do(rd, user, data) :
	if hasattr(data, 'tagid') :
		return "json", makeResponseSuccess({'tag_obj': getTag(data.tagid)})
	if hasattr(data, 'tag') :
		return "json", makeResponseSuccess({'tag_obj': getTag(data.tag)})

@app.route('/tags/get_default_blacklist.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_tags_get_default_blacklist_do(rd, user, data) :
	return "json", makeResponseSuccess({'tags': getDefaultBlacklist(data.lang)})
