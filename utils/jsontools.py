
from . import Namespace
from flask import current_app
from bson.json_util import dumps, loads

def makeResponseSuccess(data):
    return {
        "status": "SUCCEED",
        "data": data
    }

def makeResponseFailed(data):
    return {
        "status": "FAILED",
        "data": data
    }

def makeResponseError(data):
    return {
        "status": "ERROR",
        "data": data
    }

def jsonResponse(json_obj_or_str) :
    if isinstance(json_obj_or_str, str) :
        return current_app.response_class(json_obj_or_str + '\n', mimetype = current_app.config['JSONIFY_MIMETYPE'])
    else :
        return current_app.response_class(dumps(json_obj_or_str) + '\n', mimetype = current_app.config['JSONIFY_MIMETYPE'])

makeObject = Namespace.create_from_dict

