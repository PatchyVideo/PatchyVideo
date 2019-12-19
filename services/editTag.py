

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
from utils.logger import log

def queryTags(category, page_idx, page_size, order = 'none'):
	result = tagdb.list_category_tags(category)
	if isinstance(result, str):
		return result
	if order not in ['latest', 'oldest', 'count', 'count_inv'] :
		raise UserError('INCORRECT_ORDER')
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	if order == 'count':
		result = result.sort([("count", -1)])
	elif order == 'count_inv':
		result = result.sort([("count", 1)])
	return result.skip(page_idx * page_size).limit(page_size)

def queryTagsWildcard(query, category, page_idx, page_size, order):
	result = [i for i in tagdb.find_tags_wildcard(query, category, page_idx, page_size, order)][0]
	return [i for i in result['result']], result['tags_found'][0]['tags_found']

def queryTagsRegex(query, category, page_idx, page_size, order):
	result = [i for i in tagdb.find_tags_regex(query, category, page_idx, page_size, order)][0]
	return [i for i in result['result']], result['tags_found'][0]['tags_found']

def queryCategories():
	return tagdb.list_categories()

@modifyingResource('tags')
def addTag(user, tag, category, language):
	ret, sanitized_tag = verifyAndSanitizeTagOrAlias(tag)
	log(obj = {'tag': sanitized_tag, 'cat': category, 'lang': language})
	if not ret :
		raise UserError('INVALID_TAG')
	if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
		raise UserError('TAG_TOO_LONG')
	with MongoTransaction(client) as s :
		tagdb.add_tag(sanitized_tag, category, language, makeUserMeta(user), s())
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
	log(obj = {'tag': tag})
	with MongoTransaction(client) as s :
		tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
		if tag_obj and not _is_authorised(tag_obj, user, 'remove') :
			raise UserError('UNAUTHORISED_OPERATION')
		tagdb.remove_tag(tag_obj, makeUserMeta(user), session = s())
		s.mark_succeed()

@modifyingResource('tags')
def renameTagOrAddTagLanguage(user, tag, new_tag, language) :
	ret, sanitized_tag = verifyAndSanitizeTagOrAlias(new_tag)
	log(obj = {'old_tag_or_id': tag, 'new_tag': sanitized_tag, 'lang': language})
	if not ret :
		raise UserError('INVALID_TAG')
	if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
		raise UserError('TAG_TOO_LONG')
	with MongoTransaction(client) as s :
		#tag_obj = tagdb.db.tags.find_one({'tag': tag}, session = s())
		#if tag_obj and not _is_authorised(tag_obj, user, 'rename') :
		#    raise UserError('UNAUTHORISED_OPERATION')
		tagdb.add_or_rename_tag(tag, sanitized_tag, language, makeUserMeta(user), session = s())
		s.mark_succeed()

@modifyingResource('tags')
def renameOrAddAlias(user, old_name_or_tag_name, new_name) :
	ret, sanitized_alias = verifyAndSanitizeTagOrAlias(new_name)
	log(obj = {'old_name_or_tag_name': old_name_or_tag_name, 'new_name': sanitized_alias})
	if not ret :
		raise UserError('INVALID_TAG')
	if len(sanitized_alias) > TagsConfig.MAX_TAG_LENGTH :
		raise UserError('TAG_TOO_LONG')
	with MongoTransaction(client) as s :
		tagdb.add_or_rename_alias(old_name_or_tag_name, sanitized_alias, makeUserMeta(user), session = s())
		s.mark_succeed()

@modifyingResource('tags')
def removeAlias(user, alias) :
	with MongoTransaction(client) as s :
		alias_obj = tagdb.db.tag_alias.find_one({'tag': alias}, session = s())
		if alias_obj :
			log(obj = {'alias': alias, 'dst': alias_obj['dst']})
		if alias_obj and not _is_authorised(alias_obj, user, 'remove') :
			raise UserError('UNAUTHORISED_OPERATION')
		tagdb.remove_alias(alias, makeUserMeta(user), session = s())
		s.mark_succeed()

