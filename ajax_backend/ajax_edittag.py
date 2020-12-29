
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getOffsetLimitJSON
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from services.editTag import *
from config import TagsConfig

@app.route('/tags/query_categories.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_query_categories(rd, user, data):
	cats = queryCategories()
	ret = makeResponseSuccess({
		"categories": [item for item in cats]
	})
	return "json", ret

@app.route('/tags/query_tag_categories.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_query_tag_categories(rd, user, data):
	cats = queryTagCategories(data.tags)
	ret = makeResponseSuccess({
		"categorie_map": cats
	})
	return "json", ret

@app.route('/tags/query_tags.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_query_tags(rd, user, data):
	if hasattr(data, 'order') :
		order = data.order
	else :
		order = 'latest'
	if order not in ['latest', 'oldest', 'count', 'count_inv'] :
		raise AttributeError()
	offset, limit = getOffsetLimitJSON(data)
	tags = queryTags(data.category, offset, limit, order, user)
	tag_count = tags.count()
	ret = makeResponseSuccess({
		"tags": [i for i in tags],
		"count": tag_count,
		"page_count": (tag_count - 1) // limit + 1
	})
	return "json", ret

@app.route('/tags/query_tags_wildcard.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_query_tags_wildcard(rd, user, data):
	if hasattr(data, 'order') :
		order = data.order
	else :
		order = 'latest'
	if order not in ['latest', 'oldest', 'count', 'count_inv'] :
		raise AttributeError()
	if hasattr(data, 'category') :
		category = data.category
	else :
		category = ''
	offset, limit = getOffsetLimitJSON(data)
	tags, tag_count = queryTagsWildcard(data.query, category, offset, limit, order, user)
	ret = makeResponseSuccess({
		"tags": tags,
		"count": tag_count,
		"page_count": (tag_count - 1) // limit + 1
	})
	return "json", ret

@app.route('/tags/query_tags_regex.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_query_tags_regex(rd, user, data):
	if hasattr(data, 'order') :
		order = data.order
	else :
		order = 'latest'
	if hasattr(data, 'category') :
		category = data.category
	else :
		category = ''
	offset, limit = getOffsetLimitJSON(data)
	tags, tag_count = queryTagsRegex(data.query, category, offset, limit, order, user)
	ret = makeResponseSuccess({
		"tags": tags,
		"count": tag_count,
		"page_count": (tag_count - 1) // limit + 1
	})
	return "json", ret

@app.route('/tags/add_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_add_tag(rd, user, data):
	addTag(user, data.tag.strip(), data.category, data.language)

@app.route('/tags/remove_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_remove_tag(rd, user, data):
	removeTag(user, data.tag)

@app.route('/tags/transfer_category.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_transfer_category(rd, user, data):
	transferCategory(user, data.tag, data.category)

@app.route('/tags/rename_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rename_tag(rd, user, data):
	renameTagOrAddTagLanguage(user, data.tag, data.new_tag.strip(), data.language)

@app.route('/tags/rename_alias.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rename_alias(rd, user, data):
	renameOrAddAlias(user, data.tag, data.new_tag.strip())

@app.route('/tags/add_alias.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_add_alias(rd, user, data):
	renameOrAddAlias(user, int(data.tag), data.new_tag.strip())

@app.route('/tags/add_tag_language.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_add_tag_language(rd, user, data):
	renameTagOrAddTagLanguage(user, int(data.tag), data.new_tag.strip(), data.language)

@app.route('/tags/remove_alias.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_remove_alias(rd, user, data):
	removeAlias(user, data.alias)

@app.route('/tags/merge_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_merge_tag(rd, user, data):
	mergeTag(user, data.tag_dst, data.tag_src)
