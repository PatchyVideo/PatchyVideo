
from db import db, client
from bson import ObjectId
from datetime import datetime
from utils.dbtools import MongoTransaction

def createNotification(note_type : str, dst_user : ObjectId, session = None, other = None) :
    obj = {
        "type": note_type,
        "time": datetime.now(),
        "read": False,
        "to": dst_user
    }
    if other :
        for (k, v) in other.items() :
            obj[k] = v
    return db.notes.insert_one(obj, session = session).inserted_id

def getUnreadNotificationCount(user) :
    return db.notes.find({'to': user['_id'], 'read': False}).count()

def listMyNotificationUnread(user) :
    objs = db.notes.find({'to': user['_id'], 'read': False}).sort([("time", -1)])
    note_count = objs.count()
    return [i for i in objs], note_count

def listMyNotificationAll(user, offset, limit) :
    objs = db.notes.find({'to': user['_id']}).sort([("time", -1)]).skip(offset).limit(limit)
    note_count = objs.count()
    return [i for i in objs], note_count

def markRead(user, note_ids) :
    if isinstance(note_ids, str) :
        note_ids = [note_ids]
    assert isinstance(note_ids, list)
    note_ids = [ObjectId(i) for i in note_ids]
    with MongoTransaction(client) as s :
        # TODO: one can mark other's notifications as read here, add filtering later
        db.notes.update_many({'_id': {'$in': note_ids}, 'to': user['_id']}, {'$set': {'read': True}}, session = s())
        s.mark_succeed()

def markAllRead(user) :
    with MongoTransaction(client) as s :
        db.notes.update_many({'to': user['_id']}, {'$set': {'read': True}}, session = s())
        s.mark_succeed()
