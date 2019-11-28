

from utils.dbtools import makeUserMeta, MongoTransaction
from utils.tagtools import verifyAndSanitizeTag, verifyAndSanitizeAlias
from utils.rwlock import usingResource, modifyingResource

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

@modifyingResource('tags')
def addTag(user, tag, category):
    ret, sanitized_tag = verifyAndSanitizeTag(tag)
    if not ret :
        return "INVALID_TAG"
    if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
        return "TAG_TOO_LONG"
    with MongoTransaction(client) as s :
        result = tagdb.add_tag(sanitized_tag, category, makeUserMeta(user), s())
        s.mark_succeed()
        return result

def queryTagCategories(tags) :
    return tagdb.get_tag_category_map(tags)

def _is_authorised(tag_or_obj, user, op = 'remove') :
    if isinstance(tag_or_obj, str) :
        obj = tagdb.db.tags.find_one({'tag': tag_or_obj})
    else :
        obj = tag_or_obj
    creator = str(obj['meta']['created_by'])
    user_id = str(user['_id'])
    return creator == user_id or (op + 'Tag' in user['access_control']['allowed_ops']) or user['access_control']['status'] == 'admin'

@modifyingResource('tags')
def removeTag(user, tag) :
    with MongoTransaction(client) as s :
        tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
        if tag_obj is None :
            return "TAG_NOT_EXIST"
        if not _is_authorised(tag_obj, user, 'remove') :
            return "UNAUTHORISED_OPERATION"
        ret = tagdb.remove_tag(tag_obj, makeUserMeta(user), session = s())
        s.mark_succeed()
        return ret

@modifyingResource('tags')
def renameTag(user, tag, new_tag) :
    ret, sanitized_tag = verifyAndSanitizeTag(new_tag)
    if not ret :
        return "INVALID_TAG"
    if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
        return "TAG_TOO_LONG"
    with MongoTransaction(client) as s :
        tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
        if tag_obj is None :
            return "TAG_NOT_EXIST"
        if not _is_authorised(tag_obj, user, 'rename') :
            return "UNAUTHORISED_OPERATION"
        ret = tagdb.rename_tag(tag_obj, sanitized_tag, makeUserMeta(user), session = s())
        s.mark_succeed()
        return ret

@modifyingResource('tags')
def addAlias(user, alias, dst_tag) :
    ret, sanitized_alias = verifyAndSanitizeAlias(alias)
    if not ret :
        return "INVALID_TAG"
    if len(sanitized_alias) > TagsConfig.MAX_TAG_LENGTH :
        return "TAG_TOO_LONG"
    with MongoTransaction(client) as s :
        tag_obj = tagdb.db.tags.find_one({'tag': dst_tag}, session = s())
        alias_obj = tagdb.db.tags.find_one({'tag': alias}, session = s())
        if tag_obj is None :
            return "TAG_NOT_EXIST"
        if alias_obj is not None :
            return "ALIAS_EXIST"
        ret = tagdb.add_tag_alias(alias, dst_tag, makeUserMeta(user), session = s())
        s.mark_succeed()
        return ret

@modifyingResource('tags')
def removeAlias(user, alias) :
    with MongoTransaction(client) as s :
        alias_obj = tagdb.db.tags.find_one({'tag': alias}, session = s())
        if alias_obj is None :
            return "ALIAS_NOT_EXIST"
        if not _is_authorised(alias_obj, user, 'remove') :
            return "UNAUTHORISED_OPERATION"
        ret = tagdb.remove_tag_alias(alias, makeUserMeta(user), session = s())
        s.mark_succeed()
        return ret

