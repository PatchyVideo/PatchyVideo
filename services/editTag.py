

from utils.dbtools import makeUserMeta, MongoTransaction
from utils.tagtools import verifyAndSanitizeTag

from db import tagdb, client

from bson import ObjectId
from init import rdb
import redis_lock
import time

from config import TagsConfig

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
    if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
        return "TAG_LENGTH_EXCEED"
    with redis_lock.Lock(rdb, "modifyingTag"), MongoTransaction(client) as s :
        result = tagdb.add_tag(sanitized_tag, category, makeUserMeta(user), s())
        s.mark_succeed()
        return result

def queryTagCategories(tags) :
    return tagdb.get_tag_category_map(tags)

def is_authorised(tag_or_obj, user, op = 'remove') :
    if isinstance(tag_or_obj, str) :
        obj = tagdb.db.tags.find_one({'tag': tag_or_obj})
    else :
        obj = tag_or_obj
    creator = str(obj['meta']['created_by'])
    user_id = str(user['_id'])
    return creator == user_id or (op + 'Tag' in user['access_control']['allowed_ops']) or user['access_control']['status'] == 'admin'

def removeTag(user, tag) :
    with redis_lock.Lock(rdb, "modifyingTag"), MongoTransaction(client) as s :
        tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
        if tag_obj is None :
            return "TAG_NOT_EXIST"
        if not is_authorised(tag_obj, user, 'remove') :
            return "UNAUTHORISED_OPERATION"
        if tag_obj["count"] > 0 :
            return "NON_ZERO_VIDEO_REFERENCE"
        ret = tagdb.remove_tag(tag_obj, makeUserMeta(user), session = s())
        s.mark_succeed()
        return ret
    
def renameTag(user, tag, new_tag) :
    ret, sanitized_tag = verifyAndSanitizeTag(new_tag)
    if not ret :
        return "INVALID_TAG"
    if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
        return "TAG_LENGTH_EXCEED"
    with redis_lock.Lock(rdb, "modifyingTag"), MongoTransaction(client) as s :
        tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
        if tag_obj is None :
            return "TAG_NOT_EXIST"
        if not is_authorised(tag_obj, user, 'rename') :
            return "UNAUTHORISED_OPERATION"
        if tag_obj["count"] > 0 :
            return "NON_ZERO_VIDEO_REFERENCE"
        ret = tagdb.rename_tag(tag_obj, sanitized_tag, makeUserMeta(user), session = s())
        s.mark_succeed()
        return ret
