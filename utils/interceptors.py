
import json
from functools import wraps
from flask import render_template, request, jsonify, current_app, redirect, session, url_for
from types import SimpleNamespace as Namespace
from bson.json_util import dumps, loads
from init import rdb

from . import Namespace
from .jsontools import makeResponseError


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
                #return redirect(url_for(param, _external = True))
                return redirect(param)
            if command == 'render':
                return render_template(param, **rd.__dict__)
            if command == 'data':
                return param
            if command == "json":
                return current_app.response_class(dumps(param) + '\n', mimetype = current_app.config['JSONIFY_MIMETYPE'])
            return ""

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
        ret = func(*args, **kwargs)
        return _handle_return(ret, rd)
    return wrapper

def loginRequired(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'sid' in session:
            rd = Namespace()
            kwargs['user'] = _get_user_obj(session['sid'])
            if kwargs['user'] is None :
                return redirect('/login')
            rd._user = kwargs['user']
            kwargs['rd'] = rd
            ret = func(*args, **kwargs)
            return _handle_return(ret, rd)
        else :
            return redirect('/login')
    return wrapper

def loginRequiredJSON(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'sid' in session:
            rd = Namespace()
            kwargs['user'] = _get_user_obj(session['sid'])
            if kwargs['user'] is None :
                return ""
            rd._user = kwargs['user']
            kwargs['rd'] = rd
            ret = func(*args, **kwargs)
            return _handle_return(ret, rd)
        else :
            return ""
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
        ret = func(*args, **kwargs)
        return _handle_return(ret, rd)
    return wrapper

def jsonRequest(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        data = request.get_json()
        if data is None:
            return "json", makeResponseError("Request must be a JSON form")
        kwargs['data'] = Namespace.create_from_dict(data)
        try:
            ret = func(*args, **kwargs)
        except AttributeError:
            return "json", makeResponseError("Incomplete JSON form")
        return ret
    return wrapper

def ignoreError(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except Exception as e :
            import traceback
            traceback.print_stack()
        return ret
    return wrapper
