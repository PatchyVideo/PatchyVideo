import time
import os
import binascii
import re
from datetime import datetime
from bson.json_util import dumps, loads
from flask.helpers import get_template_attribute
from flask import render_template

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
from services.comment import listThread

def query_user_basic_info(uid) :
	obj = db.users.find_one({"_id": ObjectId(uid)})
	if obj is None :
		return None
	return obj['profile']

def verify_session(sid, stype) :
	session_obj = loads(rdb.get(sid).decode('utf-8'))
	if isinstance(stype, list) :
		ret = session_obj['type'] in stype
	else :
		ret = session_obj['type'] == stype
	return ret, session_obj

def login_auth_qq(openid, nickname) :
	user_obj = db.users.find_one({'profile.openid_qq': openid})
	if user_obj is not None :
		sid, _ = do_login(user_obj)
		return True, sid
	else :
		reg_sid = require_session('LOGIN_OR_SIGNUP_OPENID_QQ', openid_qq = openid)
		return False, reg_sid

def bind_qq_openid(user, openid) :
	binded_user = db.users.find_one({'profile.openid_qq': openid})
	if binded_user is not None :
		if str(binded_user['_id']) == str(user['_id']) :
			return True
		else :
			return False
	db.users.update_one({'_id': ObjectId(user['_id'])}, {'$set': {'profile.openid_qq': openid}})
	return True

def require_session(session_type, **kwargs) :
	# TODO: add challenge code to redis
	if session_type not in ['LOGIN', 'SIGNUP', 'LOGIN_OR_SIGNUP_OPENID_QQ'] :
		raise UserError('INCORRECT_SESSION_TYPE')
	sid = binascii.hexlify(bytearray(random_bytes(16))).decode()
	session_obj = {
		'type': session_type,
		'openid_qq': kwargs['openid_qq'] if session_type == 'LOGIN_OR_SIGNUP_OPENID_QQ' else ''
	}
	rdb.set(sid, dumps(session_obj), ex = UserConfig.SESSION_EXPIRE_TIME)
	log(obj = {'sid': sid})
	return sid

def logout(redis_user_key) :
	common_user_obj = rdb.get(redis_user_key)
	log(obj = {'redis_user_key': redis_user_key, 'user': common_user_obj})
	rdb.delete(redis_user_key)

def do_login(user_obj) :
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
		profile = user_obj['profile']
		profile['access_control_status'] = user_obj['access_control']['status']
		return redis_user_key, profile

	openid_qq = user_obj['profile']['openid_qq'] if 'openid_qq' in user_obj['profile'] else None
	common_user_obj = {
		'_id': user_obj['_id'],
		'profile': {
			'username': user_obj['profile']['username'],
			'image': user_obj['profile']['image'],
			'desc': user_obj['profile']['desc'],
			'email': user_obj['profile']['email'],
			'bind_qq': True if openid_qq else False
		},
		'access_control': user_obj['access_control'],
		'settings': user_obj['settings']
	}
	redis_user_value = dumps(common_user_obj)
	redis_user_key = binascii.hexlify(bytearray(random_bytes(16))).decode()
	redis_user_key_lookup_key = f"user-{user_obj['_id']}"
	rdb.set(redis_user_key, redis_user_value, ex = UserConfig.LOGIN_EXPIRE_TIME)
	rdb.set(redis_user_key_lookup_key, redis_user_key, ex = UserConfig.LOGIN_EXPIRE_TIME)
	log(obj = {'redis_user_key': redis_user_key, 'user': common_user_obj})
	profile = common_user_obj['profile']
	profile['access_control_status'] = user_obj['access_control']['status']
	return redis_user_key, profile

def unbind_qq(user) :
	def updater(obj) :
		obj['profile']['bind_qq'] = False
		return obj

	db.users.update_one({'_id': ObjectId(user['_id'])}, {'$set': {'profile.openid_qq': ''}})
	_updateUserRedisValue(user['_id'], updater)

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
	session_verified, session_obj = verify_session(login_session_id, ['LOGIN', 'LOGIN_OR_SIGNUP_OPENID_QQ'])
	if session_verified :
		user_obj = db.users.find_one({'profile.username': username})
		if not user_obj :
			user_obj = db.users.find_one({'profile.email': username.lower()})
			if not user_obj :
				log(level = 'SEC', obj = {'msg': 'USER_NOT_EXIST'})
				raise UserError('INCORRECT_LOGIN')
		crypto_method = user_obj['crypto']['crypto_method']
		if crypto_method == 'PBKDF2' :
			if not verify_password_PBKDF2(password, user_obj['crypto']['salt1'], user_obj['crypto']['password_hashed']) :
				log(level = 'SEC', obj = {'msg': 'WRONG_PASSWORD'})
				raise UserError('INCORRECT_LOGIN')
			# update crypto to Argon2
			crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = generate_user_crypto_Argon2(password)
			db.users.update_one({'_id': user_obj['_id']}, {'$set': {'crypto': {
					'crypto_method': crypto_method,
					'password_hashed': password_hashed,
					'salt1': salt1,
					'salt2': salt2,
					'master_key_encryptyed': master_key_encryptyed
				}}})
		elif crypto_method == 'Argon2' :
			if not verify_password_Argon2(password, user_obj['crypto']['salt1'], user_obj['crypto']['password_hashed']) :
				log(level = 'SEC', obj = {'msg': 'WRONG_PASSWORD'})
				raise UserError('INCORRECT_LOGIN')
		# bind QQ OpenID if present
		if session_obj['type'] == 'LOGIN_OR_SIGNUP_OPENID_QQ' :
			openid_qq = session_obj['openid_qq']
			bind_qq_openid(user_obj, openid_qq)
		return do_login(user_obj)
	raise UserError('INCORRECT_SESSION')

def query_user_batch(uids) :
	uids = [ObjectId(i) for i in uids]
	return list(db.users.aggregate([
		{'$match': {'_id': {'$in': uids}}},
		{'$project': {'profile.username': 1, 'profile.desc': 1, 'profile.image': 1, '_id': 1}}
	]))

def query_user(uid) :
	try :
		obj = db.users.find_one({'_id': ObjectId(uid)})
		del obj['access_control']
		del obj['crypto']
		del obj['settings']
		if 'email' in obj['profile'] and obj['profile']['email'] :
			em: str = obj['profile']['email']
			gravatar = md5(em.strip().lower())
			obj['profile']['gravatar'] = gravatar
		del obj['profile']['email']
		if 'openid_qq' in obj['profile'] :
			del obj['profile']['openid_qq']
	except :
		raise UserError('USER_NOT_EXIST')
	return obj

def queryBlacklist(user, language) :
	if 'blacklist' in user['settings'] :
		if isinstance(user['settings']['blacklist'], list) :
			return tagdb.translate_tag_ids_to_user_language(user['settings']['blacklist'], language)[0]
		else :
			return 'default'
	else :
		return 'default'

def queryUsername(username) :
	user_obj_find = db.users.find_one({'profile.username': username})
	if user_obj_find is None :
		raise UserError('USER_NOT_EXIST')
	del user_obj_find['access_control']
	del user_obj_find['crypto']
	del user_obj_find['settings']
	del user_obj_find['profile']['email']
	del user_obj_find['profile']['openid_qq']
	return user_obj_find

def checkIfUserExists(username) :
	user_obj_find = db.users.find_one({'profile.username': username})
	if user_obj_find is not None :
		return True
	return False

def checkIfEmailExists(email: str) :
	user_obj_find = db.users.find_one({'profile.email': email.lower()})
	if user_obj_find is not None :
		return True
	return False

def checkIsAuthorized(user, op) :
	filterOperation(op, user)

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
	session_verified, session_obj = verify_session(signup_session_id, 'SIGNUP')
	if session_verified :
		if session_obj['type'] == 'LOGIN_OR_SIGNUP_OPENID_QQ' :
			openid_qq = session_obj['openid_qq']
		else :
			openid_qq = None
		if email :
			if len(email) > UserConfig.MAX_EMAIL_LENGTH or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
				raise UserError('INCORRECT_EMAIL')
		crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = generate_user_crypto_Argon2(password)
		with redis_lock.Lock(rdb, 'signup:' + username) :
			user_obj_find = db.users.find_one({'profile.username': username})
			if user_obj_find is not None :
				raise UserError('USER_EXIST')
			if email :
				user_obj_email = db.users.find_one({'profile.email': email.lower()})
				if user_obj_email is not None :
					raise UserError('EMAIL_EXIST')
			if openid_qq :
				binded_user = db.users.find_one({'profile.openid_qq': openid_qq})
				if binded_user is not None :
					raise UserError('QQ_ALREADY_BIND')
			user_obj = {
				'profile': {
					'username': username,
					'desc': 'Write something here',
					'pubkey': '',
					'image': 'default',
					'email': email,
					'openid_qq': openid_qq if openid_qq else '' # bind if present
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
				'settings': {
					'blacklist': 'default'
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
	return photo_file

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

def update_username(redis_user_key, user_id, new_name) :
	log(obj = {'redis_user_key': redis_user_key, 'user_id': user_id, 'new_name': new_name})
	if len(new_name) > UserConfig.MAX_USERNAME_LENGTH or len(new_name) < UserConfig.MIN_USERNAME_LENGTH :
		raise UserError('NAME_LENGTH')
	user_obj_find = db.users.find_one({'profile.username': new_name})
	if user_obj_find is not None :
		raise UserError('USER_ALREADY_EXIST')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'old_name': obj['profile']['username']})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'profile.username': new_name}})

	def updater(obj) :
		obj['profile']['username'] = new_name
		return obj

	_updateUserRedisValue(user_id, updater)

def update_email(redis_user_key, user_id, new_email) :
	log(obj = {'redis_user_key': redis_user_key, 'user_id': user_id, 'new_email': new_email})
	if len(new_email) > UserConfig.MAX_EMAIL_LENGTH or not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
		raise UserError('INCORRECT_EMAIL')
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('USER_NOT_EXIST')
	user_obj_email = db.users.find_one({'profile.email': new_email})
	if user_obj_email is not None and str(user_obj_email['_id']) != str(obj['_id']) :
		raise UserError('EMAIL_EXIST')
	log(obj = {'old_email': obj['profile']['email']})
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'profile.email': new_email}})

	def updater(obj) :
		obj['profile']['email'] = new_email
		return obj

	_updateUserRedisValue(user_id, updater)

def update_blacklist(redis_user_key, user_id, blacklist) :
	log(obj = {'redis_user_key': redis_user_key, 'user_id': user_id, 'blacklist': blacklist})
	obj = db.users.find_one({'_id': ObjectId(user_id)})
	if obj is None :
		raise UserError('USER_NOT_EXIST')
	log(obj = {'old_blacklist': obj['settings']['blacklist']})
	if isinstance(blacklist, str) :
		blacklist = 'default'
	elif isinstance(blacklist, list) :
		blacklist = tagdb.filter_and_translate_tags(blacklist)
	else :
		raise UserError('INCORRECT_BLACKLIST')
	db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'settings.blacklist': blacklist}})

	def updater(obj) :
		obj['settings']['blacklist'] = blacklist
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
	log(obj = {'username': obj['profile']['username']})
	crypto_method = obj['crypto']['crypto_method']
	if crypto_method == 'PBKDF2' :
		if not verify_password_PBKDF2(old_pass, obj['crypto']['salt1'], obj['crypto']['password_hashed']) :
			raise UserError('INCORRECT_PASSWORD')
		# generate a new Argon2 security context
		crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = generate_user_crypto_Argon2(new_pass)
		crypto = {
			'crypto_method': crypto_method,
			'password_hashed': password_hashed,
			'salt1': salt1,
			'salt2': salt2,
			'master_key_encryptyed': master_key_encryptyed
		}
	elif crypto_method == 'Argon2' :
		if not verify_password_Argon2(old_pass, obj['crypto']['salt1'], obj['crypto']['password_hashed']) :
			raise UserError('INCORRECT_PASSWORD')
		crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = update_crypto_Argon2(old_pass, new_pass, obj['crypto']['salt2'], obj['crypto']['master_key_encryptyed'])
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
	if user_language not in ['CHS', 'ENG'] :
		user_language = 'ENG'
	template_file = f'PatchyVideo-passreset-{user_language}.html'
	title = get_template_attribute(template_file, 'get_title')
	html_doc = render_template(template_file, key = reset_key)
	send_noreply(email, str(title()), html_doc, mime = 'html')

def reset_password(reset_key, new_pass) :
	if len(new_pass) > UserConfig.MAX_PASSWORD_LENGTH or len(new_pass) < UserConfig.MIN_PASSWORD_LENGTH:
		raise UserError('PASSWORD_LENGTH')
	reset_key_content = rdb.get('passreset-' + reset_key)
	try :
		email = reset_key_content.decode('ascii')
		assert len(email) > 0
		obj = db.users.find_one({'profile.email': email})
		assert obj is not None
	except :
		raise UserError('INCORRECT_KEY')
	# generate a new Argon2 security context
	crypto_method, password_hashed, salt1, salt2, master_key_encryptyed = generate_user_crypto_Argon2(new_pass)
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

def listUsers(user, offset, limit, query = None, order = 'latest') :
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
	items = result.skip(offset).limit(limit)
	count = items.count()
	items = [i for i in items]
	for i in range(len(items)) :
		del items[i]["crypto"]
	return items, count

def viewOpinion(user) :
	uobj = db.users.find_one({'_id': user['_id']})
	if 'comment_thread' in uobj :
		return listThread(uobj['comment_thread'])
	else :
		return None, None
