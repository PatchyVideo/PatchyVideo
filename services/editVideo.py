
from db import tagdb, client
from utils.dbtools import makeUserMeta, MongoTransaction

from init import rdb
from bson import ObjectId
import redis_lock
from config import VideoConfig

def editVideoTags(vid, tags, user):
    tags = list(set(tags))
    item = tagdb.db.items.find_one({'_id': ObjectId(vid)})
    if item is None:
        return 'ITEM_NOT_EXIST'
    if len(tags) > VideoConfig.MAX_TAGS_PER_VIDEO:
        return "TOO_MANY_TAGS"
    with redis_lock.Lock(rdb, "videoEdit:" + item['item']['unique_id']), MongoTransaction(client) as s :
        ret = tagdb.update_item_tags(item, tags, makeUserMeta(user), s())
        if ret == 'SUCCEED':
            s.mark_succeed()
        return ret

def verifyTags(tags):
    return tagdb.verify_tags(tags)

def getVideoTags(vid) :
    return tagdb.retrive_tags(ObjectId(vid))

