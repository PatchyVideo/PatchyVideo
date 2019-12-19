
from db import db

import threading

def beginEvent(endpoint, path, obj = None) :
    pass

def setEventUser(user) :
    pass

def getEventID() :
    return ''

def setEventID(event_id) :
    pass

def setEventOp(op, event_id = None) :
    pass

def log(op = '', level = "MSG", obj = None) :
    pass

def log_e(event_id, op = '', level = "MSG", obj = None) :
    pass

def log_ne(op = '', level = "MSG", obj = None) :
    pass
