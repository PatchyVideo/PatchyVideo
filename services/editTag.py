

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
from services.tcb import filterOperation
from services.config import Config

from .authorDB import tagRemoval as authorDbTagRemoval

def getDefaultBlacklist(language) :
	return tagdb.translate_tag_ids_to_user_language([int(i) for i in Config.DEFAULT_BLACKLIST_POPULAR_TAG.split(',')], language)[0]

def getTag(tag_or_tagid) :
	if isinstance(tag_or_tagid, str) :
		tag_or_tagid = tagdb.filter_and_translate_tags([tag_or_tagid])
		if not tag_or_tagid :
			raise UserError('TAG_NOT_FOUND')
		else :
			tag_or_tagid = tag_or_tagid[0]
	obj = tagdb.db.tags.find_one({'id': tag_or_tagid})
	if obj :
		if 'icon' in obj and not obj['icon'] :
			obj['icon'] = "none"
		return obj
	raise UserError('TAG_NOT_FOUND')

def _getBlacklistTagids(user) :
	blacklist_tagids = []
	if user and 'settings' in user :
		if user['settings']['blacklist'] == 'default' :
			blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST_POPULAR_TAG.split(',')]
		else :
			blacklist_tagids = user['settings']['blacklist']
	elif user is None :
		blacklist_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST_POPULAR_TAG.split(',')]
	return blacklist_tagids

def queryTags(category, offset, limit, order = 'none', user = None):
	blacklist_tagids = _getBlacklistTagids(user)
	result = tagdb.list_category_tags(category, blacklist_tagids)
	if isinstance(result, str):
		return result
	if order not in ['latest', 'oldest', 'count', 'count_inv'] :
		raise UserError('INCORRECT_ORDER')
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	if order == 'count':
		result = result.sort([("count", 1)])
	elif order == 'count_inv':
		result = result.sort([("count", -1)])
	return result.skip(offset).limit(limit)

def queryTagsWildcard(query, category, offset, limit, order, user):
	blacklist_tagids = _getBlacklistTagids(user)
	ret = tagdb.find_tags_wildcard(query, category, offset, limit, order, blacklist_tagids)
	result = [i for i in ret][0]
	if result['tags_found'] :
		return [i for i in result['result']], result['tags_found'][0]['tags_found']
	else :
		return [], 0

def queryTagsRegex(query, category, offset, limit, order, user):
	blacklist_tagids = _getBlacklistTagids(user)
	ret = tagdb.find_tags_regex(query, category, offset, limit, order, blacklist_tagids)
	result = [i for i in ret][0]
	if result['tags_found'] :
		return [i for i in result['result']], result['tags_found'][0]['tags_found']
	else :
		return [], 0

def queryCategories():
	return tagdb.list_categories()

#@modifyingResource('tags')
def addTag(user, tag, category, language):
	addTag_impl(user, tag, category, language)

def addTag_impl(user, tag, category, language):
	ret, sanitized_tag = verifyAndSanitizeTagOrAlias(tag)
	log(obj = {'tag': sanitized_tag, 'cat': category, 'lang': language})
	filterOperation('addTag', user)
	if not ret :
		raise UserError('INVALID_TAG')
	if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
		raise UserError('TAG_TOO_LONG')
	with MongoTransaction(client) as s :
		tagdb.add_tag(sanitized_tag, category, language, makeUserMeta(user), session = s())
		s.mark_succeed()

def queryTagCategories(tags) :
	return tagdb.get_tag_category_map(tags)

@modifyingResource('tags')
def transferCategory(user, tag, new_cat) :
	log(obj = {'tag': tag, 'new_cat': new_cat})
	with MongoTransaction(client) as s :
		tag_obj = tagdb.get_tag_object(tag, session = s())
		if tag_obj :
			filterOperation('transferCategory', user, tag_obj)
		tagdb.transfer_category(tag_obj, new_cat, makeUserMeta(user), session = s())
		s.mark_succeed()

@modifyingResource('tags')
def removeTag(user, tag) :
	log(obj = {'tag': tag})
	with MongoTransaction(client) as s :
		tag_obj = tagdb.get_tag_object(tag, session = s())
		log(obj = {'tag_obj': tag_obj})
		if tag_obj :
			filterOperation('tagAdmin', user, tag_obj)
		authorDbTagRemoval(tag_obj, session = s())
		tagdb.remove_tag(tag_obj, makeUserMeta(user), session = s())
		s.mark_succeed()

@modifyingResource('tags')
def renameTagOrAddTagLanguage(user, tag, new_tag, language) :
	ret, sanitized_tag = verifyAndSanitizeTagOrAlias(new_tag)
	log(obj = {'old_tag_or_id': tag, 'new_tag': sanitized_tag, 'lang': language})
	filterOperation('renameTagOrAddTagLanguage', user)
	if not ret :
		raise UserError('INVALID_TAG')
	if len(sanitized_tag) > TagsConfig.MAX_TAG_LENGTH :
		raise UserError('TAG_TOO_LONG')
	with MongoTransaction(client) as s :
		#tag_obj = tagdb.db.tag_alias.find_one({'tag': tag}, session = s())
		#if tag_obj and not _is_authorised(tag_obj, user, 'rename') :
		#    raise UserError('UNAUTHORISED_OPERATION')
		tagdb.add_or_rename_tag(tag, sanitized_tag, language, makeUserMeta(user), session = s())
		s.mark_succeed()

@modifyingResource('tags')
def renameOrAddAlias(user, old_name_or_tag_name, new_name) :
	ret, sanitized_alias = verifyAndSanitizeTagOrAlias(new_name)
	log(obj = {'old_name_or_tag_name': old_name_or_tag_name, 'new_name': sanitized_alias})
	filterOperation('renameOrAddAlias', user)
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
			filterOperation('tagAdmin', user, alias_obj)
		tagdb.remove_alias(alias, makeUserMeta(user), session = s())
		s.mark_succeed()

@modifyingResource('tags')
def mergeTag(user, tags_dst, tag_src) :
	log(obj = {'tags_dst': tags_dst, 'tag_src': tag_src})
	filterOperation('tagAdmin', user) # only admin can do this
	with MongoTransaction(client) as s :
		tagdb.merge_tag(tags_dst, tag_src, makeUserMeta(user), session = s())
		s.mark_succeed()
