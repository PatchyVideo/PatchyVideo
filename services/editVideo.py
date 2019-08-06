
from db import tagdb, client
from utils.dbtools import makeUserMeta, MongoTransaction

from init import rdb
import redis_lock

def editVideoTags(vid, tags, user):
    with redis_lock.Lock(rdb, "videoEdit:" + str(vid)), MongoTransaction(client) as s :
        return tagdb.update_item_tags(vid, tags, makeUserMeta(user), s())

def verifyTags(tags):
    return tagdb.verify_tags(tags)


