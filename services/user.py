import time
import os
import binascii
import re
from datetime import datetime
from bson.json_util import dumps

from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta

from db import tagdb, db

from utils.crypto import *
from utils.exceptions import UserError

from bson import ObjectId
import redis_lock
from config import UserConfig
from utils.logger import log, log_ne
from services.tcb import filterOperation
from services.emailSender import send_noreply

def query_user_basic_info(uid) :
	obj = db.users.find_one({"_id": ObjectId(uid)})
	if obj is None :
		return None
	return obj['profile']

def verify_session(sid, stype) :
	ret = rdb.get(sid) == stype.encode()
	return ret

def require_session(session_type) :
	# TODO: add challenge code to redis
	if session_type not in ['LOGIN', 'SIGNUP'] :
		raise UserError('INCORRECT_SESSION_TYPE')
	sid = binascii.hexlify(bytearray(random_bytes(16))).decode()
	rdb.set(sid, session_type, ex = UserConfig.SESSION_EXPIRE_TIME)
	log(obj = {'sid': sid})
	return sid

def logout(redis_user_key) :
	common_user_obj = rdb.get(redis_user_key)
	log(obj = {'redis_user_key': redis_user_key, 'user': common_user_obj})
	rdb.delete(redis_user_key)

# we allow the same user to login multiple times and all of his login sessions are valid
def login(username, password, challenge, login_session_id) :
	log(obj = {'username': username, 'challenge': challenge, 'login_session_id': login_session_id})
	if len(username) > UserConfig.MAX_USERNAME_LENGTH :
		raise UserError('USERNAME_TOO_LONG')
	if len(username) < UserConfig.MIN_USERNAME_LENGTH :
		raise UserError('USERNAME_TOO_SHORT')
	if len(password) > UserConfig.MAX_PASSWORD_LENGTH :
		raise UserError('PASSWORD_TOO_LONG')
	if len(password) < UserConfig.MIN_PASSWORD_LENGTH :
		raise UserError('PASSWORD_TOO_SHORT')
	if verify_session(login_session_id, 'LOGIN') :
		user_obj = db.users.find_one({'profile.username': username})
		if not user_obj :
			log(level = 'SEC', obj = {'msg': 'USER_NOT_EXIST'})
			raise UserError('INCORRECT_LOGIN')
		if not verify_password_PBKDF2(password, user_obj['crypto']['salt1'], user_obj['crypto']['password_hashed']) :
			log(level = 'SEC', obj = {'msg': 'WRONG_PASSWORD'})
			raise UserError('INCORRECT_LOGIN')
		user_id = str(user_obj['_id'])
		redis_user_key_lookup_key = f"user-{user_id}"
		redis_user_key = rdb.get(redis_user_key_lookup_key)
		logged_in = False
		if redis_user_key :
			# user already logged in on some other machines
			redis_user_obj_json_str = rdb.get(redis_user_key)
			if redis_user_obj_json_str :
				logged_in = True
				# reset expire time
				rdb.set(redis_user_key, redis_user_obj_json_str, ex = UserConfig.LOGIN_EXPIRE_TIME)
				rdb.set(redis_user_key_lookup_key, redis_user_key, ex = UserConfig.LOGIN_EXPIRE_TIME)

		if logged_in :
			return redis_user_key

		common_user_obj = {
			'_id': user_obj['_id'],
			'profile': {
				'username': user_obj['profile']['username'],
				'image': user_obj['profile']['image'],
				'desc': user_obj['profile']['desc']
			},
			'access_control': user_obj['access_control']
		}
		redis_user_value = dumps(common_user_obj)
		redis_user_key = binascii.hexlify(bytearray(random_bytes(16))).decode()
		redis_user_key_lookup_key = f"user-{user_obj['_id']}"
		rdb.set(redis_user_key, redis_user_value, ex = UserConfig.LOGIN_EXPIRE_TIME)
		rdb.set(redis_user_key_lookup_key, redis_user_key, ex = UserConfig.LOGIN_EXPIRE_TIME)
		log(obj = {'redis_user_key': redis_user_key, 'user': common_user_obj})
		return redis_user_key
	raise UserError('INCORRECT_SESSION')

def query_user(uid) :
	try :
		obj = db.users.find_one({'_id': ObjectId(uid)})
		del obj['access_control']
		del obj['crypto']
	except :
		raise UserError('USER_NOT_EXIST')
	return obj

def queryUsername(username) :
	user_obj_find = db.users.find_one({'profile.username': username})
	if user_obj_find is None :
		raise UserError('USER_NOT_EXIST')
	del user_obj_find['access_control']
	del user_obj_find['crypto']
	return user_obj_find

def checkIfUserExists(username) :
	user_obj_find = db.users.find_one({'profile.username': username})
	if user_obj_find is not None :
		return True
	return False

def signup(username, password, email, challenge, signup_session_id) :
	log(obj = {'username': username, 'email': email, 'challenge': challenge, 'signup_session_id': signup_session_id})
	if len(username) > UserConfig.MAX_USERNAME_LENGTH :
		raise UserError('USERNAME_TOO_LONG')
	if len(username) < UserConfig.MIN_USERNAME_LENGTH :
		raise UserError('USERNAME_TOO_SHORT')
	if len(password) > UserConfig.MAX_PASSWORD_LENGTH :
		raise UserError('PASSWORD_TOO_LONG')
	if len(password) < UserConfig.MIN_PASSWORD_LENGTH :
		raise UserError('PASSWORD_TOO_SHORT')
	if verify_session(signup_session_id, 'SIGNUP') :
		if email :
			if len(email) > UserConfig.MAX_EMAIL_LENGTH or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
				raise UserError('INCORRECT_EMAIL')
		crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = generate_user_crypto_PBKDF2(password)
		with redis_lock.Lock(rdb, 'signup:' + username) :
			user_obj_find = db.users.find_one({'profile.username': username})
			if user_obj_find is not None :
				raise UserError('USER_EXIST')
			if email :
				user_obj_email = db.users.find_one({'profile.email': email})
				if user_obj_email is not None :
					raise UserError('EMAIL_EXIST')
			user_obj = {
				'profile': {
					'username': username,
					'desc': 'Write something here',
					'pubkey': '',
					'image': 'default',
					'email': email
				},
				'crypto': {
					'crypto_method': crypto_method,
					'password_hashed': password_hashed,
					'salt1': salt1,
					'salt2': salt2,
					'master_key_encryptyed': master_key_encryptyed
				},
				'access_control': {
					'status': 'normal',
					'access_mode': 'blacklist',
					'allowed_ops': [],
					'denied_ops': []
				},
				'meta': {
					'created_at': datetime.now()
				}
			}
			uid = db.users.insert_one(user_obj).inserted_id
			log(obj = {'uid': uid, 'profile': user_obj['profile']})
			return uid
	raise UserError('INCORRECT_SESSION')

def update_userphoto(redis_user_key, user_id, file_key) :
	log(obj = {'redis_user_key': redis_user_key, 'user_id': user_id, 'file_key': file_key})
	photo_file = None
	if file_key.startswith("upload-image-") :
		filename = rdb.get(file_key)
		if filename :
			photo_file = filename.decode('ascii')
	if photo_file is None :
		raise UserError('NO_PHOTO')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'old_photo_file': obj['profile']['image'], 'photo_file': photo_file})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'profile.image': photo_file}})

	def updater(obj) :
		obj['profile']['image'] = photo_file
		return obj

	_updateUserRedisValue(user_id, updater)

def update_desc(redis_user_key, user_id, new_desc) :
	log(obj = {'redis_user_key': redis_user_key, 'user_id': user_id, 'new_desc': new_desc})
	if len(new_desc) > UserConfig.MAX_DESC_LENGTH :
		raise UserError('DESC_TOO_LONG')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'old_desc': obj['profile']['desc']})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'profile.desc': new_desc}})

	def updater(obj) :
		obj['profile']['desc'] = new_desc
		return obj

	_updateUserRedisValue(user_id, updater)

def update_email(redis_user_key, user_id, new_email) :
	log(obj = {'redis_user_key': redis_user_key, 'user_id': user_id, 'new_email': new_email})
	if len(new_email) > UserConfig.MAX_EMAIL_LENGTH or not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
		raise UserError('INCORRECT_EMAIL')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'old_email': obj['profile']['email']})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'profile.email': new_email}})

	def updater(obj) :
		obj['profile']['email'] = new_email
		return obj

	_updateUserRedisValue(user_id, updater)

def update_password(user_id, old_pass, new_pass) :
	if len(old_pass) > UserConfig.MAX_PASSWORD_LENGTH or len(old_pass) < UserConfig.MIN_PASSWORD_LENGTH:
		raise UserError('PASSWORD_LENGTH')
	if len(new_pass) > UserConfig.MAX_PASSWORD_LENGTH or len(new_pass) < UserConfig.MIN_PASSWORD_LENGTH:
		raise UserError('PASSWORD_LENGTH')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('USER_NOT_EXIST')
	if not verify_password_PBKDF2(old_pass, obj['crypto']['salt1'], obj['crypto']['password_hashed']) :
		raise UserError('INCORRECT_PASSWORD')
	crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = update_crypto_PBKDF2(old_pass, new_pass, obj['crypto']['salt2'], obj['crypto']['master_key_encryptyed'])
	crypto = {
		'crypto_method': crypto_method,
		'password_hashed': password_hashed,
		'salt1': salt1,
		'salt2': salt2,
		'master_key_encryptyed': master_key_encryptyed
	}
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'crypto': crypto}})

def request_password_reset(email, user_language) :
	user_obj = db.users.find_one({'profile.email': email})
	if user_obj is None :
		raise UserError('EMAIL_NOT_EXIST')
	reset_key = random_bytes_str(16)
	rdb.set('passreset-' + reset_key, email)
	send_noreply(email, '找回密码', '点击下方的链接重置密码:\n%s%s' % ('https://patchyvideo.com/resetpassword?key=', reset_key))

def reset_password(reset_key, new_pass) :
	if len(new_pass) > UserConfig.MAX_PASSWORD_LENGTH or len(new_pass) < UserConfig.MIN_PASSWORD_LENGTH:
		raise UserError('PASSWORD_LENGTH')
	reset_key_content = rdb.get('passreset' + reset_key)
	try :
		email = reset_key_content.decode('ascii')
		assert len(email) > 0
		obj = db.users.find_one({'profile.email': email})
		assert obj is not None
	except :
		raise UserError('INCORRECT_KEY')
	crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = update_crypto_PBKDF2(None, new_pass, obj['crypto']['salt2'], obj['crypto']['master_key_encryptyed'])
	crypto = {
		'crypto_method': crypto_method,
		'password_hashed': password_hashed,
		'salt1': salt1,
		'salt2': salt2,
		'master_key_encryptyed': master_key_encryptyed
	}
	db.users.update_one({'_id': obj['_id']}, {'$set': {'crypto': crypto}})

def _updateUserRedisValue(user_id, updater) :
	redis_user_key_lookup_key = f"user-{str(user_id)}"
	redis_user_key_ttl = rdb.ttl(redis_user_key_lookup_key)
	redis_user_key = rdb.get(redis_user_key_lookup_key)
	if redis_user_key :
		redis_user_obj_json = rdb.get(redis_user_key)
		if redis_user_obj_json :
			redis_user_obj = loads(redis_user_obj_json)
			redis_user_obj = updater(redis_user_obj)
			rdb.set(redis_user_key, dumps(redis_user_obj), ex = redis_user_key_ttl)

def whoAmI(user) :
	return user['access_control']['status']

def updateUserRole(user_id, role, user) :
	filterOperation('updateUserRole', user, user_id)
	old_user_obj = db.users.find_one({'_id': ObjectId(user_id)})
	if old_user_obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'user_id': user_id, 'new_role': role, 'old_role': old_user_obj['access_control']['status']})
	if role not in ['normal', 'admin'] :
		raise UserError('INCORRECT_ROLE')
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'access_control.status': role}})

	def updater(obj) :
		obj['access_control']['status'] = role
		return obj
	
	_updateUserRedisValue(user_id, updater)
	
def updateUserAccessMode(user_id, mode, user) :
	filterOperation('updateUserAccessMode', user, user_id)
	old_user_obj = db.users.find_one({'_id': ObjectId(user_id)})
	if old_user_obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'user_id': user_id, 'new_mode': mode, 'old_mode': old_user_obj['access_control']['access_mode']})
	if mode not in ['blacklist', 'whitelist'] :
		raise UserError('INCORRECT_ACCESS_MODE')
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'access_control.access_mode': mode}})

	def updater(obj) :
		obj['access_control']['access_control'] = mode
		return obj
	
	_updateUserRedisValue(user_id, updater)

def getUserAllowedOps(user_id, user) :
	filterOperation('getUserAllowedOps', user, user_id)
	old_user_obj = db.users.find_one({'_id': ObjectId(user_id)})
	if old_user_obj is None :
		raise UserError('USER_NOT_EXIST')
	return old_user_obj['access_control']['allowed_ops']

def updateUserAllowedOps(user_id, allowed_ops, user) :
	filterOperation('updateUserAllowedOps', user, user_id)
	old_user_obj = db.users.find_one({'_id': ObjectId(user_id)})
	if old_user_obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'user_id': user_id, 'new_ops': allowed_ops, 'old_ops': old_user_obj['access_control']['allowed_ops']})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'access_control.allowed_ops': allowed_ops}})

	def updater(obj) :
		obj['access_control']['allowed_ops'] = allowed_ops
		return obj
	
	_updateUserRedisValue(user_id, updater)

def getUserDeniedOps(user_id, user) :
	filterOperation('getUserDeniedOps', user, user_id)
	old_user_obj = db.users.find_one({'_id': ObjectId(user_id)})
	if old_user_obj is None :
		raise UserError('USER_NOT_EXIST')
	return old_user_obj['access_control']['denied_ops']

def updateUserDeniedOps(user_id, denied_ops, user) :
	filterOperation('updateUserDeniedOps', user, user_id)
	old_user_obj = db.users.find_one({'_id': ObjectId(user_id)})
	if old_user_obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'user_id': user_id, 'new_ops': denied_ops, 'old_ops': old_user_obj['access_control']['denied_ops']})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'access_control.denied_ops': denied_ops}})

	def updater(obj) :
		obj['access_control']['denied_ops'] = denied_ops
		return obj
	
	_updateUserRedisValue(user_id, updater)

def listUsers(user, page_idx, page_size, query = None, order = 'latest') :
	filterOperation('listUsers', user)
	if order not in ['latest', 'oldest'] :
		raise UserError('INCORRECT_ORDER')
	if query :
		query = re.escape(query)
		query = f'^.*{query}.*$'
		query_obj = {'profile.username': {'$regex': query}}
	else :
		query_obj = {}
	result = db.users.find(query_obj)
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	items = result.skip(page_idx * page_size).limit(page_size)
	count = items.count()
	items = [i for i in items]
	for i in range(len(items)) :
		del items[i]["crypto"]
	return items, count
