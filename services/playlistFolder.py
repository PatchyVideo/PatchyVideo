"""
playlist folder:
{
  "_id": ...,
  "user": ObjectId(<uid>),
  "leaf": True,
  "playlist": ObjectId(<pid>),
  "name": null,
  "path": '/touhou/hand_drawn/\<pid>\/'
}
{
  "_id": ...,
  "user": ObjectId(<uid>),
  "leaf": False,
  "playlist": null,
  "name": "anime",
  "path": "/touhou/hand_drawn/anime/"
}
{
  "_id": ...,
  "user": ObjectId(<uid>),
  "leaf": False,
  "playlist": null,
  "name": "hand_drawn",
  "path": "/touhou/hand_drawn/"
}
{
  "_id": ...,
  "user": ObjectId(<uid>),
  "leaf": False,
  "playlist": null,
  "name": "touhou",
  "path": "/touhou/"
}
// No / folder

funcs:
checkFolderExists(user, path)
createFolder(user, root, name, privateView = False, privateEdit = True)
deleteFolder(user, path)
copyFolder(user, dst_root, path)
#copyFolderFromOtherUser(dst_user, dst_root, src_user, src_path)
moveFolder(user, dst_root, path)
renameFolder(user, path, new_name)
changeFolderAccess(user, path, privateView, privateEdit)
addPlaylistsToFolder(user, path, [playlists])
removePlaylistsFromFolder(user, path, [playlists])

listFolder(user, path)
"""

from init import rdb
from db import client, db

from utils.exceptions import UserError
from utils.rwlock import usingResource, modifyingResource
from utils.logger import log
from utils.dbtools import makeUserMeta, makeUserMetaObject, MongoTransaction
from services.tcb import filterOperation

import re
import redis_lock

from bson import ObjectId
from datetime import datetime

def _verifyPath(path) :
	if path :
		if path[0] == '/' and path[-1] == '/' :
			return True
	raise UserError('INVALID_PATH')

def _verifyFolderName(name) :
	if '/' in name or '\\' in name or '*' in name :
		raise UserError('INVALID_PATH')
	return True

def _joinPath(a, b) :
	return a + b + "/"

def _parentPath(p) :
	return p[: p[: -1].rfind('/') + 1], p[p[: -1].rfind('/') + 1: -1]

def _findFolder(user, path, raise_exception = True) :
	user_id = makeUserMeta(user)
	obj = db.playlist_folders.find_one({'user': user_id, 'path': path})
	if obj is None :
		if path == '/' :
			with MongoTransaction(client) as s :
				obj = {
					'user': makeUserMeta(user),
					'leaf': False,
					'playlist': None,
					'name': "",
					'path': "/",
					'privateView': False,
					'privateEdit': True,
					'meta': makeUserMetaObject(user)
				}
				db.playlist_folders.insert_one(obj, session = s())
				s.mark_succeed()
			return obj
		else :
			if raise_exception :
				raise UserError('FOLDER_NOT_EXIST')
			else :
				return None
	return obj

def deletePlaylist(pid, session) :
	db.playlist_folders.delete_many({'playlist': ObjectId(pid)}, session = session)

def createFolder(user, root, name, privateView = False, privateEdit = True) :
	filterOperation('createFolder', user, root)
	_verifyPath(root)
	_verifyFolderName(name)
	with redis_lock.Lock(rdb, f"folderEdit:{str(makeUserMeta(user))}:{root}") :
		_findFolder(user, root)
		fullpath = root + name + "/"

		with redis_lock.Lock(rdb, f"folderEdit:{str(makeUserMeta(user))}:{fullpath}"), MongoTransaction(client) as s :
			obj = _findFolder(user, fullpath, raise_exception = False)
			if obj :
				raise UserError('FOLDER_ALREADY_EXIST')
			folder_obj = {
				'user': makeUserMeta(user),
				'leaf': False,
				'playlist': None,
				'name': name,
				'path': fullpath,
				'privateView': privateView,
				'privateEdit': privateEdit,
				'meta': makeUserMetaObject(user)
			}
			db.playlist_folders.insert_one(folder_obj, session = s())
			s.mark_succeed()

def deleteFolder(user, path) :
	_verifyPath(path)

	with redis_lock.Lock(rdb, f"folderEdit:{str(makeUserMeta(user))}:{path}"), MongoTransaction(client) as s :
		folder_obj = _findFolder(user, path)
		filterOperation('deleteFolder', user, folder_obj)

		path_escaped = re.escape(path)
		query_regex = f'^{path_escaped}.*'
		db.playlist_folders.delete_many({'user': makeUserMeta(user), 'path': {'$regex': query_regex}}, session = s())
		s.mark_succeed()

def deleteFolders(user, paths) :
	for path in paths :
		deleteFolder(user, path)
	
def copyFolder(user, dst_root, path) :
	pass
def moveFolder(user, dst_root, path) :
	pass

def renameFolder(user, path, new_name) :
	_verifyPath(path)
	_verifyFolderName(new_name)
	if path == "/" :
		raise UserError('INVALID_PATH')

	with redis_lock.Lock(rdb, f"folderEdit:{str(makeUserMeta(user))}:{path}"), MongoTransaction(client) as s :
		folder_obj = _findFolder(user, path)
		filterOperation('renameFolder', user, folder_obj)

		parent_path, cur_folder = _parentPath(path)
		if '\\' in cur_folder :
			raise UserError('INVALID_PATH')
		parent_path_escaped = re.escape(parent_path)
		cur_folder_esacped = re.escape(cur_folder)
		query_regex = f'^{parent_path_escaped}{cur_folder_esacped}\\/.*'
		replace_regex = re.compile(f'^({parent_path_escaped})({cur_folder_esacped})(\\/.*)')
		paths = db.playlist_folders.find({'user': makeUserMeta(user), 'path': {'$regex': query_regex}}, session = s())
		db.playlist_folders.update_one({'user': makeUserMeta(user), 'path': {'$regex': f'^{parent_path_escaped}{cur_folder_esacped}\\/$'}}, {'$set': {'name': new_name}}, session = s())
		for p in paths :
			new_path = replace_regex.sub(rf'\1{new_name}\3', p['path'])
			db.playlist_folders.update_one({'_id': p['_id']}, {'$set': {'path': new_path}}, session = s())
		db.playlist_folders.update_one({'user': makeUserMeta(user), 'path': {'$regex': query_regex}}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()
		}}, session = s())
		s.mark_succeed()

def changeFolderAccess(user, path, privateView, privateEdit, recursive = True) :
	_verifyPath(path)

	with redis_lock.Lock(rdb, f"folderEdit:{str(makeUserMeta(user))}:{path}"), MongoTransaction(client) as s :
		folder_obj = _findFolder(user, path)
		filterOperation('changeFolderAccess', user, folder_obj)

		path_escaped = re.escape(path)
		if recursive :
			query_regex = f'^{path_escaped}.*'
		else :
			query_regex = f'^{path_escaped}$'
		db.playlist_folders.update_many(
		{
			'user': makeUserMeta(user),
			'path': {'$regex': query_regex}
		},
		{
			'$set': {
				'privateView': privateView,
				'privateEdit': privateEdit
			}
		}, session = s())
		db.playlist_folders.update_one({'_id': folder_obj['_id']}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()
		}}, session = s())
		s.mark_succeed()

def addPlaylistsToFolder(user, path, playlists) :
	_verifyPath(path)

	with redis_lock.Lock(rdb, f"folderEdit:{str(makeUserMeta(user))}:{path}"), MongoTransaction(client) as s :
		folder_obj = _findFolder(user, path)
		filterOperation('addPlaylistsToFolder', user, folder_obj)

		for pid in playlists :
			playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
			if playlist is None :
				continue # skip non-exist playlist
			if playlist['private'] and not filterOperation('viewPrivatePlaylist', user, playlist, raise_exception = False) :
				continue # skip other's private playlist
			playlist_path = path + "\\" + str(playlist['_id']) + "\\/"
			if _findFolder(user, playlist_path, raise_exception = False) :
				continue # skip duplicated playlist
			playlist_obj = {
				'user': makeUserMeta(user),
				'leaf': True,
				'playlist': playlist['_id'],
				'name': None,
				'path': playlist_path,
				'privateView': folder_obj['privateView'],
				'privateEdit': folder_obj['privateEdit'],
				'meta': makeUserMetaObject(user)
			}
			db.playlist_folders.insert_one(playlist_obj, session = s())

		db.playlist_folders.update_one({'_id': folder_obj['_id']}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()
		}}, session = s())
		s.mark_succeed()


def removePlaylistsFromFolder(user, path, playlists) :
	_verifyPath(path)

	with redis_lock.Lock(rdb, f"folderEdit:{str(makeUserMeta(user))}:{path}"), MongoTransaction(client) as s :
		folder_obj = _findFolder(user, path)
		filterOperation('addPlaylistsToFolder', user, folder_obj)

		for pid in playlists :
			fullpath = path + "\\" + pid + "\\/"
			path_escaped = re.escape(fullpath)
			query_regex = f'^{path_escaped}.*'
			db.playlist_folders.delete_one({'user': makeUserMeta(user), 'path': {'$regex': query_regex}}, session = s())

		db.playlist_folders.update_one({'_id': folder_obj['_id']}, {'$set': {
			'meta.modified_by': makeUserMeta(user),
			'meta.modified_at': datetime.now()
		}}, session = s())
		s.mark_succeed()

def listFolder(viewing_user, user, path) :
	_verifyPath(path)
	folder_obj = _findFolder(user, path)
	if folder_obj['privateView'] :
		filterOperation('listFolder', viewing_user, folder_obj)

	path_escaped = re.escape(path)
	query_regex = f'^{path_escaped}[^\\/]*\\/$'
	ret = db.playlist_folders.aggregate([
		{'$match': {'user': makeUserMeta(user), 'path': {'$regex': query_regex}}},
		{'$lookup': {'from': 'playlists', 'localField': 'playlist', 'foreignField': '_id', 'as': 'playlist_object'}},
		{'$unwind': {'path': '$playlist_object', 'preserveNullAndEmptyArrays': True}},
		{'$sort': {'path': 1}}
	])
	items = [i for i in ret]
	ans = []
	
	for item in items :
		assert not (('playlist_object' in item) ^ item['leaf'])
		if item['privateView'] and (viewing_user is None or (str(user['_id']) != str(viewing_user['_id']) and viewing_user['status'] != 'admin')) :
			continue
		if 'playlist_object' in item : # playlist item (leaf)
			if item['playlist_object'] is None : # leaf playlist does not exist, do not display
				# TODO: maybe just display it is gone, not deleting it
				with MongoTransaction(client) as s :
					db.playlist_folders.delete_one({'user': makeUserMeta(user), 'path': item['path']}, session = s())
					s.mark_succeed()
			elif item['playlist_object']['private'] : # playlist is private
				if filterOperation('viewPrivatePlaylist', viewing_user, item['playlist_object'], raise_exception = False) :
					ans.append(item)
				else :
					item['playlist_object'] = 'PRIVATE_PLAYLIST'
					ans.append(item)
			else :
				ans.append(item)
		else : # subfolder item
			ans.append(item)
	return ans

def test() :
	pass
