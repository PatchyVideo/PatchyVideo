
from . import Namespace
from flask import current_app
from bson.json_util import dumps, loads

def makeResponseSuccess(data):
	return {
		"status": "SUCCEED",
		"data": data
	}

def makeResponseFailed(data):
	if isinstance(data, str) :
		return {
			"status": "FAILED",
			"data": ".",
			"dataerr": {"reason": data}
		}
	else :
		return {
			"status": "FAILED",
			"data": ".",
			"dataerr": data
		}

def makeResponseError(data):
	if isinstance(data, str) :
		return {
			"status": "ERROR",
			"data": ".",
			"dataerr": {"reason": data}
		}
	else :
		return {
			"status": "ERROR",
			"data": ".",
			"dataerr": data
		}
		
def jsonResponse(json_obj_or_str) :
	if isinstance(json_obj_or_str, str) :
		return current_app.response_class(json_obj_or_str + '\n', mimetype = "application/json")
	else :
		return current_app.response_class(dumps(json_obj_or_str) + '\n', mimetype = "application/json")

makeObject = Namespace.create_from_dict

