

from utils.dbtools import makeUserMeta, MongoTransaction
from utils.tagtools import verifyAndSanitizeTagOrAlias, verifyAndSanitizeLanguage
from utils.rwlock import usingResource, modifyingResource
from utils.exceptions import UserError

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
        result = result.sort([("meta.created_at", -1)])
    if order == 'oldest':
        result = result.sort([("meta.created_at", 1)])
    if order == 'count':
        result = result.sort([("count", -1)])
    elif order == 'count_inv':
        result = result.sort([("count", 1)])
    return result.skip(page_idx * page_size).limit(page_size)

def queryTagsWildcard(query, category, page_idx, page_size, order = 'none'):
    result = tagdb.find_tags_wildcard(query, category)
    if isinstance(result, str):
        return result
    if order == 'latest':
        result = result.sort([("meta.created_at", -1)])
    if order == 'oldest':
        result = result.sort([("meta.created_at", 1)])
    if order == 'count':
        result = result.sort([("count", -1)])
    elif order == 'count_inv':
        result = result.sort([("count", 1)])
    return result.skip(page_idx * page_size).limit(page_size)

def queryTagsRegex(query, category, page_idx, page_size, order = 'none'):
    result = tagdb.find_tags_regex(query, category)
    if isinstance(result, str):
        return result
    if order == 'latest':
        result = result.sort([("meta.created_at", -1)])
    elif order == 'oldest':
        result = result.sort([("meta.created_at", 1)])
    elif order == 'count':
        result = result.sort([("count", -1)])
    elif order == 'count_inv':
        result = result.sort([("count", 1)])
    return result.skip(page_idx * page_size).limit(page_size)

def queryCategories():
    return tagdb.list_categories()

@modifyingResource('tags')
def addTag(user, tag, category, language):
    ret, sanitized_tag = verifyAndSanitizeTagOrAlias(tag)
    if not ret :
        raise UserError('INVALID_TAG')
    ret, sanitized_lang = verifyAndSanitizeLanguage(language)
    if not ret :
        raise UserError('INVALID_LANGUAGE')
    if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
        raise UserError('TAG_TOO_LONG')
    with MongoTransaction(client) as s :
        tagdb.add_tag(sanitized_tag, category, sanitized_lang, makeUserMeta(user), s())
        s.mark_succeed()

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
        if tag_obj and not _is_authorised(tag_obj, user, 'remove') :
            raise UserError('UNAUTHORISED_OPERATION')
        tagdb.remove_tag(tag_obj, makeUserMeta(user), session = s())
        s.mark_succeed()

@modifyingResource('tags')
def renameTag(user, tag, new_tag) :
    ret, sanitized_tag = verifyAndSanitizeTagOrAlias(new_tag)
    if not ret :
        raise UserError('INVALID_TAG')
    if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
        raise UserError('TAG_TOO_LONG')
    with MongoTransaction(client) as s :
        tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
        if tag_obj and not _is_authorised(tag_obj, user, 'rename') :
            raise UserError('UNAUTHORISED_OPERATION')
        tagdb.rename_tag(tag_obj, sanitized_tag, makeUserMeta(user), session = s())
        s.mark_succeed()

@modifyingResource('tags')
def addAlias(user, alias, dst_tag) :
    ret, sanitized_alias = verifyAndSanitizeTagOrAlias(alias)
    if not ret :
        raise UserError('INVALID_TAG')
    if len(sanitized_alias) > TagsConfig.MAX_TAG_LENGTH :
        raise UserError('TAG_TOO_LONG')
    with MongoTransaction(client) as s :
        alias_obj = tagdb.db.tags.find_one({'tag': alias}, session = s())
        if alias_obj is not None :
            raise UserError('ALIAS_EXIST')
        tagdb.add_tag_alias(sanitized_alias, dst_tag, 'regular', '', makeUserMeta(user), session = s())
        s.mark_succeed()

@modifyingResource('tags')
def addTagLanguage(user, alias, dst_tag, language) :
    ret, sanitized_alias = verifyAndSanitizeTagOrAlias(alias)
    if not ret :
        raise UserError('INVALID_ALIAS')
    ret, sanitized_lang = verifyAndSanitizeLanguage(language)
    if not ret :
        raise UserError('INVALID_LANGUAGE')
    with MongoTransaction(client) as s :
        alias_obj = tagdb.db.tags.find_one({'tag': alias}, session = s())
        if alias_obj is not None and 'type' in alias_obj and alias_obj['type'] == 'language' :
            # you can overwrite an existing regular alias with a language one
            raise UserError('ALIAS_EXIST')
        tagdb.add_tag_alias(sanitized_alias, dst_tag, 'language', sanitized_lang, makeUserMeta(user), session = s())
        s.mark_succeed()

@modifyingResource('tags')
def removeAlias(user, alias) :
    with MongoTransaction(client) as s :
        alias_obj = tagdb.db.tags.find_one({'tag': alias}, session = s())
        if alias_obj and not _is_authorised(alias_obj, user, 'remove') :
            raise UserError('UNAUTHORISED_OPERATION')
        tagdb.remove_tag_alias(alias, makeUserMeta(user), session = s())
        s.mark_succeed()

@modifyingResource('tags')
def updateTagLanguage(user, tag, language) :
    with MongoTransaction(client) as s :
        tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
        if tag_obj and not _is_authorised(tag_obj, user, 'edit') :
            raise UserError('UNAUTHORISED_OPERATION')
        tagdb.update_tag_language(tag, language, makeUserMeta(user), session = s())
        s.mark_succeed()

