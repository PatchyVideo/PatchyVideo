
from bson import ObjectId
from datetime import datetime

from init import rdb
from db import tagdb, db, client
from utils.exceptions import UserError
from utils.dbtools import makeUserMetaObject, makeUserMeta
from .tagStatistics import getPopularTags, getCommonTags, updateTagSearch
from services.tcb import filterOperation
from utils.dbtools import MongoTransaction
from services.config import Config
from db.TagDB_language import VALID_LANGUAGES
from datetime import datetime

import redis_lock

VALID_SUBTITLE_FORMAT = [
    'srt',
    'vtt'
]

def getSubtitle(subid: ObjectId) :
    sub_item = db.subtitles.find_one({'_id': subid})
    if sub_item is None :
        raise UserError('ITEM_NOT_FOUND')
    return sub_item

def postSubtitle(user, vid: ObjectId, language: str, subformat: str, content: str) :
    if language not in VALID_LANGUAGES :
        raise UserError('INVALID_LANGUAGE')
    subformat = subformat.lower()
    if subformat not in VALID_SUBTITLE_FORMAT :
        raise UserError('INVALID_SUBTITLE_FORMAT')
    video_item = tagdb.retrive_item(vid)
    if video_item is None :
        raise UserError('VIDEO_NOT_FOUND')
    filterOperation('postSubtitle', user)
    with redis_lock.Lock(rdb, "videoEdit:" + video_item['item']['unique_id']), MongoTransaction(client) as s :
        existing_item = db.subtitles.find_one({'vid': vid, 'lang': language, 'format': subformat, 'meta.created_by': makeUserMeta(user)}, session = s())
        if existing_item is None :
            subid = db.subtitles.insert_one({
                'vid': vid,
                'lang': language,
                'format': subformat,
                'content': content,
                'meta': makeUserMetaObject(user)
            }, session = s()).inserted_id
        else :
            db.subtitles.update_one({'_id': existing_item['_id']}, {
                '$set': {
                    'content': content,
                    'meta.modified_at': datetime.utcnow()
                }
            }, session = s())
            subid = existing_item['_id']
        return ObjectId(subid)

def requireSubtitleOCR(user, vid, translate_to = '') :
    pass

def listVideoSubtitles(vid: ObjectId) :
    items = list(db.subtitles.aggregate([
        {'$match': {'vid': vid}},
        {'$lookup': {'from': 'users', 'localField': 'meta.created_by', 'foreignField': '_id', 'as': 'user_obj'}},
        {'$project': {'lang': 1, 'format': 1, 'meta': 1, 'user_obj._id': 1, 'user_obj.profile.username': 1, 'user_obj.profile.image': 1}},
        {'$sort': {"meta.modified_at": -1}}
    ]))
    return items


