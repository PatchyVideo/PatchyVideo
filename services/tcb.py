
from db import tagdb, client
from utils.exceptions import UserError
from utils.dbtools import makeUserMeta, MongoTransaction

"""
Level 0: Only (authorised) admin level user can view
Level 1: admin level user and uploader can view
Level 2: Only geistered used can view
Level 3: Everyone can view
"""

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

def filterOperation(op_name, user, item_id = None, raise_error = True) :
	pass

def setVideoClearence(vid, clearence, user) :
	if clearence >= 0 and clearence <= 3 :
		filterOperation('setVideoClearence', user, vid)
		with MongoTransaction(client) as s :
			tagdb.set_item_clearence(vid, clearence, user, s())
	else :
		raise UserError('INCORRECT_CLEARENCE')
