
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.editTag import addTag, queryTags, queryCategories, queryTagCategories, removeTag, renameTag
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
    tags = queryTags(data.category, data.page - 1, data.page_size, 'latest')
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
    #print('Adding tag %s to %s' % (data.tag, data.category))
    data.tag = data.tag.strip()
    if len(data.tag) > TagsConfig.MAX_TAG_LENGTH or len(data.category) > TagsConfig.MAX_CATEGORY_LENGTH :
        return "json", makeResponseFailed("Tag or category length too large(%d characters for tag)" % TagsConfig.MAX_TAG_LENGTH)
    ret = addTag(user, data.tag, data.category)
    if ret == 'SUCCEED':
        response = makeResponseSuccess("SUCCEED")
    if ret == 'INVALID_TAG':
        response = makeResponseFailed("This tag name(%s) is invalid" % (data.tag))
    if ret == 'TAG_EXIST':
        response = makeResponseFailed("This tag(%s) already exists" % (data.tag))
    if ret == 'CATEGORY_NOT_EXIST':
        response = makeResponseFailed("This category(%s) does not exist" % (data.category))
    return "json", response

@app.route('/tags/remove_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_remove_tag(rd, user, data):
    return "json", makeResponseFailed("You are not authorised to do this")
    ret = removeTag(user, data.tag)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("SUCCEED")
    elif ret == 'TAG_NOT_EXIST' :
        response = makeResponseFailed("This tag(%s) does not exist" % (data.tag))
    elif ret == 'UNAUTHORISED_OPERATION' :
        response = makeResponseFailed("You are not authorised to do this")
    return "json", response

@app.route('/tags/rename_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rename_tag(rd, user, data):
    return "json", makeResponseFailed("You are not authorised to do this")
    ret = renameTag(user, data.tag, data.new_tag)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("SUCCEED")
    elif ret == 'TAG_NOT_EXIST' :
        response = makeResponseFailed("This tag(%s) does not exist" % (data.tag))
    elif ret == 'TAG_EXIST' :
        response = makeResponseFailed("This tag(%s) already exist" % (data.tag_new))
    elif ret == 'UNAUTHORISED_OPERATION' :
        response = makeResponseFailed("You are not authorised to do this")
    return "json", response
