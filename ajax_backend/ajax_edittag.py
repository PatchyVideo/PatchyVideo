
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.editTag import addTag, queryTags, queryCategories, queryTagCategories, removeTag, renameTag, addAlias, removeAlias, addTagLanguage, queryTagsWildcard, queryTagsRegex
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
    tags = queryTags(data.category, data.page - 1, data.page_size, order)
    tag_count = tags.count()
    ret = makeResponseSuccess({
        "tags": [i for i in tags],
        "count": tag_count,
        "page_count": (tag_count - 1) // data.page_size + 1
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
    if hasattr(data, 'category') :
        category = data.category
    else :
        category = ''
    tags = queryTagsWildcard(data.query, category, data.page - 1, data.page_size, order)
    tag_count = tags.count()
    ret = makeResponseSuccess({
        "tags": [i for i in tags],
        "count": tag_count,
        "page_count": (tag_count - 1) // data.page_size + 1
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
    tags = queryTagsRegex(data.query, category, data.page - 1, data.page_size, order)
    tag_count = tags.count()
    ret = makeResponseSuccess({
        "tags": [i for i in tags],
        "count": tag_count,
        "page_count": (tag_count - 1) // data.page_size + 1
    })
    return "json", ret

@app.route('/tags/add_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_add_tag(rd, user, data):
    data.tag = data.tag.strip()
    ret = addTag(user, data.tag, data.category)
    if ret == 'SUCCEED':
        response = makeResponseSuccess("SUCCEED")
    else :
        response = makeResponseFailed(ret)
    return "json", response

@app.route('/tags/remove_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_remove_tag(rd, user, data):
    return "json", makeResponseFailed("UNAUTHORISED_OPERATION")
    ret = removeTag(user, data.tag)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("SUCCEED")
    else :
        response = makeResponseFailed(ret)
    return "json", response


@app.route('/tags/rename_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rename_tag(rd, user, data):
    ret = renameTag(user, data.tag, data.new_tag)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("SUCCEED")
    else :
        response = makeResponseFailed(ret)
    return "json", response

@app.route('/tags/add_alias.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_add_alias(rd, user, data):
    ret = addAlias(user, data.alias, data.dst_tag)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("SUCCEED")
    else :
        response = makeResponseFailed(ret)
    return "json", response

@app.route('/tags/add_tag_language.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_add_tag_language(rd, user, data):
    ret = addTagLanguage(user, data.alias, data.dst_tag, data.language)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("SUCCEED")
    else :
        response = makeResponseFailed(ret)
    return "json", response

@app.route('/tags/remove_alias.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_remove_alias(rd, user, data):
    ret = removeAlias(user, data.alias)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("SUCCEED")
    else :
        response = makeResponseFailed(ret)
    return "json", response

