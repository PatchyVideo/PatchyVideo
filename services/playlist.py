
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, makeUserMetaObject, MongoTransaction

from spiders import dispatch
from db import tagdb, db, client

from datetime import datetime
from bson import ObjectId

import redis_lock

MAX_VIDEO_PER_PLAYLIST = 10000

def getPlaylist(pid) :
    return db.playlists.find_one({'_id': ObjectId(pid)})

def is_authorised(pid_or_obj, user, op = 'edit') :
    if isinstance(pid_or_obj, str) :
        obj = db.playlists.find_one({'_id': ObjectId(pid_or_obj)})
    else :
        obj = pid_or_obj
    creator = str(obj['meta']['created_by'])
    user_id = str(user['_id'])
    return creator == user_id

def createPlaylist(language, title, desc, cover, user) :
    obj = {"title": {language: title}, "desc": {language: desc}, "views": 0, "videos": 0, "cover": cover, "meta": makeUserMetaObject(user)}
    pid = db.playlists.insert_one(obj)
    return str(pid.inserted_id)

def removePlaylist(pid, user) :
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
            s.mark_failover()
            return "PLAYLIST_NOT_EXIST"
        if not is_authorised(pid, user) :
            s.mark_failover()
            return "UNAUTHORISED_OPERATION"
        db.playlist_items.delete_many({"pid": ObjectId(pid)}, session = s())
        db.playlists.delete_one({"_id": ObjectId(pid)}, session = s())
        return "SUCCEED"

def updatePlaylistInfo(pid, language, title, desc, cover, user) :
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        if db.playlists.find_one({'_id': ObjectId(pid)}) is None :
            s.mark_failover()
            return "PLAYLIST_NOT_EXIST"
        if not is_authorised(pid, user) :
            s.mark_failover()
            return "UNAUTHORISED_OPERATION"
        if user is not None :
            db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                "title.%s" % language: title,
                "desc.%s" % language: desc,
                'meta.modified_by': ObjectId(user['_id']),
                'meta.modified_at': datetime.now()}}, session = s())
        else :
            db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                "title.%s" % language: title,
                "desc.%s" % language: desc,
                'meta.modified_by': '',
                'meta.modified_at': datetime.now()}}, session = s())
        if cover :
            db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {"cover": cover}}, session = s())
        return "SUCCEED"

def addVideoToPlaylist(pid, vid, user) :
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
        if playlist is None :
            s.mark_failover()
            return "PLAYLIST_NOT_EXIST"
        if not is_authorised(playlist, user) :
            s.mark_failover()
            return "UNAUTHORISED_OPERATION"
        if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
            s.mark_failover()
            return "VIDEO_NOT_EXIST"
        if playlist["videos"] > 2000 :
            s.mark_failover()
            return "VIDEO_LIMIT_EXCEEDED"
        if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
            s.mark_failover()
            return "VIDEO_ALREADY_EXIST"
        playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
        playlists.append(ObjectId(pid))
        playlists = list(set(playlists))
        tagdb.update_item_query(vid, {'$set': {'item.series': playlists}}, session = s())
        db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": playlist["videos"], "meta": makeUserMeta(user)}, session = s())
        db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
        if user is not None :
            db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                'meta.modified_by': ObjectId(user['_id']),
                'meta.modified_at': datetime.now()}}, session = s())
        else :
            db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                'meta.modified_by': '',
                'meta.modified_at': datetime.now()}}, session = s())
        return "SUCCEED"

def listPalylistVideos(pid, page_idx, page_size) :
    playlist = db.playlists.find_one({'_id': ObjectId(pid)})
    if playlist is None :
        return "PLAYLIST_NOT_EXIST", None, 0
    ans_obj = db.playlist_items.aggregate([
        {
            '$match': {
                "pid": ObjectId(pid)
            }
        },
        {
            '$lookup': {
                'from': "items",
                'localField': "vid",
                'foreignField': "_id",
                'as': 'item'
            }
        },
        {
            '$unwind': {
                'path': '$item'
            }
        },
        {
            '$sort' : {
                'rank' : 1
            }
        },
        {
            '$skip' : page_idx * page_size,
        },
        {
            '$limit' : page_size
        }
    ])
    ret = []
    for obj in ans_obj:
        ret_obj = obj['item']
        ret_obj['rank'] = obj['rank']
        ret.append(ret_obj)
    return "SUCCEED", ret, playlist['videos']

def listPlaylists(page_idx, page_size, query = {}, order = 'latest') :
    ans_obj = db.playlists.find(query)
    if order == 'latest':
        ans_obj = ans_obj.sort([("meta.created_at", 1)])
    if order == 'oldest':
        ans_obj = ans_obj.sort([("meta.created_at", -1)])
    if order == 'views':
        ans_obj = ans_obj.sort([("views", 1)])
    return "SUCCEED", ans_obj.skip(page_idx * page_size).limit(page_size)

def listPlaylistsForVideo(vid) :
    video = tagdb.retrive_item({'_id': ObjectId(vid)})
    if video is None :
        return "VIDEO_NOT_EXIST"
    result = db.playlist_items.aggregate([
        {
            '$match': {
                '$and': [
                {
                    'pid': {
                        '$in': video['item']['series']
                    }
                },
                {
                    'vid': video['_id']
                }]
            }
        },
        {
            '$lookup': {
                'from': 'playlists',
                'localField': 'pid',
                'foreignField': '_id',
                'as': 'playlist'
            }
        },
        {
            '$unwind': {
                'path': '$playlist'
            }
        }
    ])
    ans = []
    for obj in result :
        playlist_obj = obj['playlist']
        playlist_obj['prev'] = ''
        playlist_obj['next'] = ''
        rank = obj['rank']
        if rank > 0 :
            playlist_obj['prev'] = str(db.playlist_items.find_one({'$and': [{'pid': playlist_obj['_id']}, {'rank': rank - 1}]})['vid'])
        if rank + 1 < playlist_obj['videos'] :
            playlist_obj['next'] = str(db.playlist_items.find_one({'$and': [{'pid': playlist_obj['_id']}, {'rank': rank + 1}]})['vid'])
        ans.append(playlist_obj)
    return ans

def removeVideoFromPlaylist(pid, vid, user) :
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
        if playlist is None :
            s.mark_failover()
            return "PLAYLIST_NOT_EXIST"
        if not is_authorised(playlist, user) :
            s.mark_failover()
            return "UNAUTHORISED_OPERATION"
        if playlist["videos"] > 0 :
            entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
            if entry is None :
                s.mark_failover()
                return "VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST"
            db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gt': entry['rank']}}]}, {'$inc': {'rank': -1}}, session = s())
            db.playlist_items.delete_one({'_id': entry['_id']}, session = s())
            db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": -1}}, session = s())
            if user is not None :
                db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                    'meta.modified_by': ObjectId(user['_id']),
                    'meta.modified_at': datetime.now()}}, session = s())
            else :
                db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                    'meta.modified_by': '',
                    'meta.modified_at': datetime.now()}}, session = s())
        else :
            return "EMPTY_PLAYLIST"
        return "SUCCEED"

def editPlaylist_MoveUp(pid, vid, user) :
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
        if playlist is None :
            s.mark_failover()
            return "PLAYLIST_NOT_EXIST"
        if not is_authorised(playlist, user) :
            s.mark_failover()
            return "UNAUTHORISED_OPERATION"
        if playlist["videos"] > 0 :
            entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
            if entry is None :
                s.mark_failover()
                return "VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST"
            if entry['rank'] <= 0 :
                return "SUCCEED"
            exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": entry['rank'] - 1}, session = s())
            db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': entry['rank'] - 1}}, session = s())
            db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': entry['rank']}}, session = s())
            if user is not None :
                db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                    'meta.modified_by': ObjectId(user['_id']),
                    'meta.modified_at': datetime.now()}}, session = s())
            else :
                db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                    'meta.modified_by': '',
                    'meta.modified_at': datetime.now()}}, session = s())
            return "SUCCEED"
        else :
            return "EMPTY_PLAYLIST"

def editPlaylist_MoveDown(pid, vid, user) :
     with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
        if playlist is None :
            s.mark_failover()
            return "PLAYLIST_NOT_EXIST"
        if not is_authorised(playlist, user) :
            s.mark_failover()
            return "UNAUTHORISED_OPERATION"
        if playlist["videos"] > 0 :
            entry = db.playlist_items.find_one({"pid": ObjectId(pid), "vid": ObjectId(vid)}, session = s())
            if entry is None :
                s.mark_failover()
                return "VIDEO_NOT_EXIST_OR_NOT_IN_PLAYLIST"
            if entry['rank'] >= playlist["videos"] - 1 :
                return "SUCCEED"
            exchange_entry = db.playlist_items.find_one({"pid": ObjectId(pid), "rank": entry['rank'] + 1}, session = s())
            db.playlist_items.update_one({'_id': entry['_id']}, {'$set': {'rank': entry['rank'] + 1}}, session = s())
            db.playlist_items.update_one({'_id': exchange_entry['_id']}, {'$set': {'rank': entry['rank']}}, session = s())
            if user is not None :
                db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                    'meta.modified_by': ObjectId(user['_id']),
                    'meta.modified_at': datetime.now()}}, session = s())
            else :
                db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                    'meta.modified_by': '',
                    'meta.modified_at': datetime.now()}}, session = s())
            return "SUCCEED"
        else :
            return "EMPTY_PLAYLIST"

def insertIntoPlaylist(pid, vid, rank, user) :
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        playlist = db.playlists.find_one({'_id': ObjectId(pid)}, session = s())
        if playlist is None :
            s.mark_failover()
            return "PLAYLIST_NOT_EXIST"
        if not is_authorised(playlist, user) :
            s.mark_failover()
            return "UNAUTHORISED_OPERATION"
        if tagdb.retrive_item({'_id': ObjectId(vid)}, session = s()) is None :
            s.mark_failover()
            return "VIDEO_NOT_EXIST"
        if playlist["videos"] > 2000 :
            s.mark_failover()
            return "VIDEO_LIMIT_EXCEEDED"
        if db.playlist_items.find_one({'$and': [{'pid': ObjectId(pid)}, {'vid': ObjectId(vid)}]}, session = s()) is not None :
            s.mark_failover()
            return "VIDEO_ALREADY_EXIST"
        if rank < 0 or rank > playlist['videos'] :
            s.mark_failover()
            return "OUT_OF_RANGE"
        playlists = tagdb.retrive_item({'_id': ObjectId(vid)}, session = s())['item']['series']
        playlists.append(ObjectId(pid))
        playlists = list(set(playlists))
        tagdb.update_item_query(vid, {'$set': {'item.series': playlists}}, session = s())
        db.playlists.update_one({"_id": ObjectId(pid)}, {"$inc": {"videos": 1}}, session = s())
        db.playlist_items.update_many({'$and': [{'pid': ObjectId(pid)}, {'rank': {'$gte': rank}}]}, {'$inc': {'rank': 1}}, session = s())
        db.playlist_items.insert_one({"pid": ObjectId(pid), "vid": ObjectId(vid), "rank": rank, "meta": makeUserMeta(user)}, session = s())
        if user is not None :
            db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                'meta.modified_by': ObjectId(user['_id']),
                'meta.modified_at': datetime.now()}}, session = s())
        else :
            db.playlists.update_one({'_id': ObjectId(pid)}, {'$set': {
                'meta.modified_by': '',
                'meta.modified_at': datetime.now()}}, session = s())
        return "SUCCEED"
