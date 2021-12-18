
from db import tagdb, client
from utils.exceptions import UserError
from utils.dbtools import makeUserMeta, MongoTransaction
from bson import ObjectId

"""
Level 0: Only (authorised) admin level user can view
Level 1: admin level user and uploader can view
Level 2: Only registered used can view
Level 3: Everyone can view
"""

def generate_clearence_search_term(user) :
	return {'clearence': {'$gte': 3}}

def _is_authorised(item, user) :
	item_clearence = item['clearence']
	if not user :
		if item_clearence == 3 :
			return True
		else :
			return False
	else :
		if item_clearence == 3 :
			return True
		elif item_clearence == 2 :
			return True
		elif item_clearence == 1 :
			if user['access_control']['status'] == 'admin' or str(user['_id']) == str(item['meta']['created_by']) :
				return True
			else :
				return False
		elif item_clearence == 0 :
			if user['access_control']['status'] == 'admin' :
				return True
			else :
				return False
	return False

def filterVideoList(videos, user) :
	return list(filter(lambda x: _is_authorised(x, user), videos))

def filterSingleVideo(vid, user, raise_error = True) :
	item = tagdb.retrive_item(vid)
	if item is None :
		return None
	if _is_authorised(item, user) :
		return item
	else :
		if raise_error :
			raise UserError('ITEM_NOT_FOUND')
		else :
			return None

# Your default privileges, which is your starting rights
_DEFAULT_OPS = [
	'breakLink', 'syncTags', 'broadcastTags',
	'addTag', 'renameTagOrAddTagLanguage', 'renameOrAddAlias', 'transferCategory',
	'editVideoTags', 'refreshVideoDetail', 'refreshVideoDetailURL',
	'createPlaylist',
	'postVideo',
	'createFolder', 'listFolder',
	'createOrModifyAuthorRecord',
	'setVideoRepostType',
	'addSubs', 'delSubs', 'updateSubs',
	'postComment',
	'postThreadToForum',
	'postSubtitle', 'requestSubtitleOCR',
	'sendDM']

def _check_object_agnostic(op_name, user, raise_exception = True) :
	if user['access_control']['access_mode'] == 'blacklist' :
		if op_name in user['access_control']['denied_ops'] :
			# user is specifically denied of this operation, he is deemed unauthorised even if he is the onwer of an object
			if raise_exception :
				raise UserError('UNAUTHORISED_OPERATION')
			else :
				return False
		user_allowed_ops = list(set(user['access_control']['allowed_ops']) | set(_DEFAULT_OPS))
		if op_name not in user_allowed_ops :
			return False
	else :
		user_allowed_ops = user['access_control']['allowed_ops']
		if op_name not in user_allowed_ops :
			# user is in whitelist mode, he can only do things given by allowed_ops
			if raise_exception :
				raise UserError('UNAUTHORISED_OPERATION')
			else :
				return False
	return True

def _check_object_specific(op_name, user, item_obj) :
	if isinstance(item_obj, dict) :
		if str(item_obj['meta']['created_by']) == str(user['_id']) :
			return True
		if 'privateEdit' in item_obj and not item_obj['privateEdit'] and not op_name.startswith('remove') and not op_name.startswith('del') :
			return True
		if 'item' in item_obj and 'privateEdit' in item_obj['item'] and not item_obj['item']['privateEdit'] and not op_name.startswith('remove') and not op_name.startswith('del') :
			return True
	elif isinstance(item_obj, str) or isinstance(item_obj, ObjectId) :
		pass
	return False

def isObjectAgnosticOperationPermitted(op_name, user) :
	if user is None :
		return False
	if user['access_control']['status'] == 'admin' :
		return True
	return _check_object_agnostic(op_name, user)

def filterOperation(op_name, user, item_id = None, raise_exception = True) :
	"""
	If you are not the creator of item_id, then unless op_name is part of your rights, you will be denied
	"""
	if not user :
		if raise_exception :
			raise UserError('UNAUTHORISED_OPERATION')
		else :
			return False
	if user['access_control']['status'] == 'admin' :
		return True

	if _check_object_agnostic(op_name, user) or _check_object_specific(op_name, user, item_id) :
		return True

	if raise_exception :
		raise UserError('UNAUTHORISED_OPERATION')
	else :
		return False

def setVideoClearence(vid, clearence, user) :
	if clearence >= 0 and clearence <= 3 :
		filterOperation('setVideoClearence', user, vid)
		item = filterSingleVideo(vid, user)
		if item is None:
			raise UserError('ITEM_NOT_FOUND')
		if item['clearence'] < clearence :
			raise UserError('ITEM_NOT_FOUND')
		with MongoTransaction(client) as s :
			tagdb.set_item_clearence(vid, clearence, user, session = s())
			s.mark_succeed()
	else :
		raise UserError('INCORRECT_CLEARENCE')
