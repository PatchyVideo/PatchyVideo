
import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.editTag import addTag, queryTags, queryCategories, queryTagCategories, removeTag, renameTag


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
    if len(data.tag) > 48 or len(data.category) > 16 :
        return "json", makeResponseFailed("Tag or category length too large(48 characters for tag)")
    ret = addTag(user, data.tag, data.category)
    if ret == 'SUCCEED':
        response = makeResponseSuccess("Success")
    if ret == 'INVALID_TAG':
        response = makeResponseFailed("This tag name(%s) is invalid" % (data.tag))
    if ret == 'TAG_EXIST':
        response = makeResponseFailed("This tag(%s) already exist in %s" % (data.tag, data.category))
    if ret == 'CATEGORY_NOT_EXIST':
        response = makeResponseFailed("This category(%s) does not exist" % (data.category))
    return "json", response

@app.route('/tags/remove_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_remove_tag(rd, user, data):
    ret = removeTag(user, data.tag)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("Success")
    if ret == 'TAG_NOT_EXIST' :
        response = makeResponseFailed("This tag(%s) does not exist" % (data.tag))
    if ret == 'UNAUTHORISED_OPERATION' :
        response = makeResponseFailed("You are not authorised to do this")
    if ret == 'NON_ZERO_VIDEO_REFERENCE' :
        response = makeResponseFailed("This tag(%s) is being referenced by video(s), please remove these references first" % (data.tag))
    return "json", response

@app.route('/tags/rename_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rename_tag(rd, user, data):
    ret = renameTag(user, data.tag, data.new_tag)
    if ret == 'SUCCEED' :
        response = makeResponseSuccess("Success")
    if ret == 'TAG_NOT_EXIST' :
        response = makeResponseFailed("This tag(%s) does not exist" % (data.tag))
    if ret == 'TAG_EXIST' :
        response = makeResponseFailed("This tag(%s) already exist" % (data.tag_new))
    if ret == 'UNAUTHORISED_OPERATION' :
        response = makeResponseFailed("You are not authorised to do this")
    if ret == 'NON_ZERO_VIDEO_REFERENCE' :
        response = makeResponseFailed("This tag(%s) is being referenced by video(s), please remove these references first" % (data.tag))
    return "json", response
