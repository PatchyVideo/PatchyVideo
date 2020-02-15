
import os
import sys
import json
import urllib
import traceback
from functools import wraps
from flask import render_template, request, jsonify, current_app, redirect, session, url_for, abort
from werkzeug.exceptions import HTTPException
from types import SimpleNamespace as Namespace
from bson.json_util import dumps, loads
from init import rdb#, logger

from . import Namespace

from .jsontools import makeResponseError, makeResponseFailed, makeResponseSuccess, jsonResponse
from .exceptions import UserError

if os.getenv("VERSION", "") == "" :
	_VERSION_URL = "https://github.com/zyddnys/PatchyVideo/"
	_VERSION = "v0.1"
else :
	_VERSION = os.getenv("VERSION", "")[:16]
	_VERSION_URL = "https://github.com/zyddnys/PatchyVideo/commit/" + os.getenv("VERSION", "")

from utils.logger import beginEvent, setEventUser, log, log_e
from utils.http import getRealIP

def _handle_return(ret, rd):
	if isinstance(ret, str):
		s = ret.split(':')
		if len(s) == 2:
			if s[0] == 'redirect':
				return redirect(s[1])
			if s[0] == 'render':
				return render_template(ret, **rd.__dict__)
		elif len(s) == 1:
			return render_template(ret, **rd.__dict__)
	elif isinstance(ret, tuple):
		if len(ret) == 2:
			command, param = ret
			if command == 'redirect':
				return redirect(param)
			if command == 'render':
				return render_template(param, **rd.__dict__)
			if command == 'data':
				return param
			if command == "json":
				return jsonResponse(param)
			return ""
	else :
		return ret

def _get_user_obj(sid) :
	obj_json = rdb.get(sid)
	if obj_json is None :
		return None
	return loads(obj_json)

def basePage(func):
	@wraps(func)
	def wrapper(*args, **kwargs) :
		beginEvent(func.__name__, getRealIP(request), request.full_path, request.args)
		rd = Namespace()
		rd._version = _VERSION
		rd._version_url = _VERSION_URL
		kwargs['rd'] = rd
		try:
			ret = func(*args, **kwargs)
			return _handle_return(ret, rd)
		except HTTPException as e:
			log(level = 'WARN', obj = {'ex': e})
			raise e
		except Exception as ex:
			log(level = 'ERR', obj = {'ex': str(ex)})
			abort(400)
	return wrapper

def basePageNoLog(func):
	@wraps(func)
	def wrapper(*args, **kwargs) :
		rd = Namespace()
		rd._version = _VERSION
		rd._version_url = _VERSION_URL
		kwargs['rd'] = rd
		try:
			ret = func(*args, **kwargs)
			return _handle_return(ret, rd)
		except HTTPException as e:
			raise e
		except :
			abort(400)
	return wrapper

def loginRequired(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		beginEvent(func.__name__, getRealIP(request), request.full_path, request.args)
		path = request.full_path
		if path[-1] == '?' :
			path = path[:-1]
		encoded_url = urllib.parse.quote(path)
		if 'sid' in session:
			rd = Namespace()
			rd._version = _VERSION
			rd._version_url = _VERSION_URL
			kwargs['user'] = _get_user_obj(session['sid'])
			if kwargs['user'] is None :
				log('login_check', level = 'SEC', obj = {'action': 'denied', 'path': request.full_path, 'sid': session['sid']})
				return redirect('/login?redirect_url=' + encoded_url)
			rd._user = kwargs['user']
			setEventUser(rd._user)
			kwargs['rd'] = rd
			try:
				ret = func(*args, **kwargs)
				return _handle_return(ret, rd)
			except HTTPException as e:
				log(level = 'WARN', obj = {'ex': e})
				raise e
			except UserError as ue :
				log(level = 'WARN', obj = {'ue': str(ue)})
				if 'NOT_EXIST' in ue.msg :
					abort(404)
				elif ue.msg == 'UNAUTHORISED_OPERATION' :
					abort(403)
				else :
					abort(400)
			except Exception as ex:
				log(level = 'ERR', obj = {'ex': str(ex)})
				abort(400)
		else :
			log('login_check', level = 'SEC', obj = {'action': 'denied', 'path': request.full_path})
			return redirect('/login?redirect_url=' + encoded_url)
	return wrapper

def loginRequiredJSON(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		beginEvent(func.__name__, getRealIP(request), request.full_path, request.args)
		if 'sid' in session:
			rd = Namespace()
			kwargs['user'] = _get_user_obj(session['sid'])
			if kwargs['user'] is None :
				log('login_check', level = 'SEC', obj = {'action': 'denied', 'path': request.full_path, 'sid': session['sid']})
				return jsonResponse(makeResponseError("UNAUTHORISED_OPERATION"))
			rd._user = kwargs['user']
			setEventUser(rd._user)
			kwargs['rd'] = rd
			ret = func(*args, **kwargs)
			return _handle_return(ret, rd)
		else :
			log('login_check', level = 'SEC', obj = {'action': 'denied', 'path': request.full_path})
			return jsonResponse(makeResponseError("UNAUTHORISED_OPERATION"))
	return wrapper

def loginOptional(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		beginEvent(func.__name__, getRealIP(request), request.full_path, request.args)
		rd = Namespace()
		if 'sid' in session:
			kwargs['user'] = _get_user_obj(session['sid'])
		else :
			kwargs['user'] = None
		rd._user = kwargs['user']
		if rd._user :
			setEventUser(rd._user)
		rd._version = _VERSION
		rd._version_url = _VERSION_URL
		kwargs['rd'] = rd
		try:
			ret = func(*args, **kwargs)
			return _handle_return(ret, rd)
		except HTTPException as e:
			log(level = 'WARN', obj = {'ex': e})
			raise e
		except UserError as ue :
			log(level = 'WARN', obj = {'ue': str(ue)})
			if 'NOT_EXIST' in ue.msg :
				abort(404)
			elif ue.msg == 'UNAUTHORISED_OPERATION' :
				abort(403)
			else :
				abort(400)
		except Exception as ex :
			log(level = 'ERR', obj = {'ex': str(ex)})
			abort(400)
	return wrapper

def jsonRequest(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		data = request.get_json()
		if data is None:
			return jsonResponse(makeResponseFailed("INCORRECT_REQUEST"))
		kwargs['data'] = Namespace.create_from_dict(data)
		try:
			ret = func(*args, **kwargs)
		except AttributeError as ex:
			log(level = 'WARN', obj = {'ex': str(ex)})
			return jsonResponse(makeResponseFailed("INCORRECT_REQUEST"))
		except ValueError as ex:
			log(level = 'WARN', obj = {'ex': str(ex)})
			return jsonResponse(makeResponseFailed("INCORRECT_REQUEST"))
		except HTTPException as e:
			raise e
		except UserError as ue:
			log(level = 'WARN', obj = {'ue': str(ue)})
			return jsonResponse(makeResponseFailed({"reason": ue.msg, "aux": ue.aux}))
		except Exception as ex:
			log(level = 'ERR', obj = {'ex': str(ex)})
			abort(400)
		if not ret :
			return "json", makeResponseSuccess({})
		else :
			return ret
	return wrapper

from aiohttp import web

def asyncJsonRequest(func) :
	@wraps(func)
	async def wrapper(*args, **kwargs) :
		ret = await func(*args, **kwargs)
		return web.json_response(ret, dumps = dumps)
	return wrapper
