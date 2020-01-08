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
	obj = db.users.find_one({'_id': ObjectId(uid)})
	del obj['access_control']
	del obj['crypto']
	return obj

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

def update_desc(redis_user_key, user_id, new_desc) :
	log(obj = {'redis_user_key': redis_user_key, 'user_id': user_id, 'new_desc': new_desc})
	if len(new_desc) > UserConfig.MAX_DESC_LENGTH :
		raise UserError('DESC_TOO_LONG')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('INCORRECT_LOGIN')
	log(obj = {'old_desc': obj['profile']['desc']})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'profile.desc': new_desc}})
	common_user_obj = {
			'_id': ObjectId(obj['_id']),
			'profile': {
				'username': obj['profile']['username'],
				'image': obj['profile']['image'],
				'desc': new_desc
			},
			'access_control': obj['access_control']
		}
	redis_user_value = dumps(common_user_obj)
	rdb.set(redis_user_key, redis_user_value, ex = int(time.time() + UserConfig.LOGIN_EXPIRE_TIME))

def update_password(user_id, old_pass, new_pass) :
	if len(old_pass) > UserConfig.MAX_PASSWORD_LENGTH or len(old_pass) < UserConfig.MIN_PASSWORD_LENGTH:
		raise UserError('PASSWORD_LENGTH')
	if len(new_pass) > UserConfig.MAX_PASSWORD_LENGTH or len(new_pass) < UserConfig.MIN_PASSWORD_LENGTH:
		raise UserError('PASSWORD_LENGTH')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('INCORRECT_LOGIN')
	if not verify_password_PBKDF2(old_pass, obj['crypto']['salt1'], obj['crypto']['password_hashed']) :
		raise UserError('INCORRECT_LOGIN')
	crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = update_crypto_PBKDF2(old_pass, new_pass, obj['crypto']['salt2'], obj['crypto']['master_key_encryptyed'])
	crypto = {
		'crypto_method': crypto_method,
		'password_hashed': password_hashed,
		'salt1': salt1,
		'salt2': salt2,
		'master_key_encryptyed': master_key_encryptyed
	}
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'crypto': crypto}})

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
