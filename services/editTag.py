
"""
File:
    editTag.py
Location:
    /services/editTag.py
Description:
    Service module for editing tags
"""

from utils.dbtools import makeUserMeta, MongoTransaction
from utils.tagtools import verifyAndSanitizeTag

from db import tagdb, client

from init import rdb
import redis_lock

def queryTags(category, page_idx, page_size, order = 'none'):
    result = tagdb.list_category_tags(category)
    if isinstance(result, str):
        return result
    if order == 'latest':
        result = result.sort([("meta.created_at", 1)])
    if order == 'oldest':
        result = result.sort([("meta.created_at", -1)])
    if order == 'count':
        result = result.sort([("count", -1)])
    return result.skip(page_idx * page_size).limit(page_size)

def queryCategories():
    return tagdb.list_categories()

def addTag(user, tag, category):
    ret, sanitized_tag = verifyAndSanitizeTag(tag)
    if not ret :
        return "INVALID_TAG"
    with redis_lock.Lock(rdb, "addTag:" + category), MongoTransaction(client) as s :
        result = tagdb.add_tag(sanitized_tag, category, makeUserMeta(user), s())
        return result

