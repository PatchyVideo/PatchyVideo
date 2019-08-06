"""
File:
    ajax_edittag.py
Location:
    /ajax_backend/ajax_edittag.py
Description:
    Handle editTag AJAX post
"""

import time

import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch

from services.editTag import addTag, queryTags, queryCategories

"""
Function:
    ajax_query_categories
Location:
    /ajax_backend/ajax_edittag.py
Description:
    handle query tag categories from webpages
"""
@app.route('/tags/query_categories.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_query_categories(rd, user, data):
    cats = queryCategories()
    ret = makeResponseSuccess({
        "categories": [item for item in cats]
    })
    return "json", ret

"""
Function:
    ajax_query_tags
Location:
    /ajax_backend/ajax_edittag.py
Description:
    handle tag query from webpages
"""
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

"""
Function:
    ajax_add_tag
Location:
    /ajax_backend/ajax_edittag.py
Description:
    handle add tag query from webpages
"""
@app.route('/tags/add_tag.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_add_tag(rd, user, data):
    #print('Adding tag %s to %s' % (data.tag, data.category))
    if len(data.tag) > 48 or len(data.category) > 16 :
        return "json", makeResponseFailed("Tag or category length too large(48 characters for tag)")
    ret = addTag(user, data.tag, data.category)
    if ret == 'SUCCESS':
        response = makeResponseSuccess("Success")
    if ret == 'INVALID_TAG':
        response = makeResponseFailed("This tag name(%s) is invalid" % (data.tag))
    if ret == 'TAG_EXIST':
        response = makeResponseFailed("This tag(%s) already exist in %s" % (data.tag, data.category))
    if ret == 'CATEGORY_NOT_EXIST':
        response = makeResponseFailed("This category(%s) does not exist" % (data.category))
    return "json", response

