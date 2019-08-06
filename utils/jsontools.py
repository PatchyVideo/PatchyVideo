
from . import Namespace

def makeResponseSuccess(data):
    return {
        "status": "success",
        "data": data
    }

def makeResponseFailed(data):
    return {
        "status": "failed",
        "data": data
    }

def makeResponseError(data):
    return {
        "status": "error",
        "data": data
    }

makeObject = Namespace.create_from_dict

