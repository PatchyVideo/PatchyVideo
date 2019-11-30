
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
		rd = Namespace()
		kwargs['rd'] = rd
		try:
			ret = func(*args, **kwargs)
			return _handle_return(ret, rd)
		except HTTPException as e:
			raise e
		except:
			print('****Exception!', file = sys.stderr)
			print(traceback.format_exc(), file = sys.stderr)
			abort(400)
	return wrapper

def loginRequired(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		path = request.full_path
		if path[-1] == '?' :
			path = path[:-1]
		encoded_url = urllib.parse.quote(path)
		if 'sid' in session:
			rd = Namespace()
			kwargs['user'] = _get_user_obj(session['sid'])
			if kwargs['user'] is None :
				return redirect('/login?redirect_url=' + encoded_url)
			rd._user = kwargs['user']
			kwargs['rd'] = rd
			#logger.info('PAGE_U - %s - %s' % (kwargs['rd']._user['profile']['username'], func.__name__))
			try:
				ret = func(*args, **kwargs)
				return _handle_return(ret, rd)
			except HTTPException as e:
				raise e
			except:
				print('****Exception!', file = sys.stderr)
				print(traceback.format_exc(), file = sys.stderr)
				abort(400)
		else :
			return redirect('/login?redirect_url=' + encoded_url)
	return wrapper

def loginRequiredJSON(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		if 'sid' in session:
			rd = Namespace()
			kwargs['user'] = _get_user_obj(session['sid'])
			if kwargs['user'] is None :
				#logger.warning('JSON - %s - Access Denied' % func.__name__)
				return jsonResponse(makeResponseError("UNAUTHORISED_OPERATION"))
			rd._user = kwargs['user']
			kwargs['rd'] = rd
			ret = func(*args, **kwargs)
			return _handle_return(ret, rd)
		else :
			#logger.warning('JSON - %s - Access Denied' % func.__name__)
			return jsonResponse(makeResponseError("UNAUTHORISED_OPERATION"))
	return wrapper

def loginOptional(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		rd = Namespace()
		if 'sid' in session:
			kwargs['user'] = _get_user_obj(session['sid'])
		else :
			kwargs['user'] = None
		rd._user = kwargs['user']
		kwargs['rd'] = rd
		try:
			ret = func(*args, **kwargs)
			return _handle_return(ret, rd)
		except HTTPException as e:
			raise e
		except:
			print('****Exception!', file = sys.stderr)
			print(traceback.format_exc(), file = sys.stderr)
			abort(400)
	return wrapper

def jsonRequest(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		data = request.get_json()
		if data is None:
			return jsonResponse(makeResponseFailed("INCORRECT_REQUEST"))
		kwargs['data'] = Namespace.create_from_dict(data)
		"""if hasattr(kwargs['rd'], '_user') :
			logger.info('JSON_U - %s - %s - %s' % (kwargs['rd']._user['profile']['username'], func.__name__, dumps(data)))
		else :
			logger.info('JSON_A - %s - %s' % (func.__name__, dumps(kwargs['data'])))"""
		try:
			ret = func(*args, **kwargs)
		except AttributeError:
			return jsonResponse(makeResponseFailed("INCORRECT_REQUEST"))
		except ValueError:
			return jsonResponse(makeResponseFailed("INCORRECT_REQUEST"))
		except HTTPException as e:
			raise e
		except UserError as ue:
			return jsonResponse(makeResponseFailed({"reason": ue.msg, "aux": ue.aux}))
		except:
			print('****Exception!', file = sys.stderr)
			print(traceback.format_exc(), file = sys.stderr)
			abort(400)
		if not ret :
			return "json", makeResponseSuccess({})
		else :
			return ret
	return wrapper

def ignoreError(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			ret = func(*args, **kwargs)
			return ret
		except:
			pass
		return None
	return wrapper
