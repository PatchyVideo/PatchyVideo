
from db import tagdb, client
from utils.dbtools import makeUserMeta, MongoTransaction
from utils.rwlock import usingResource, modifyingResource
from utils.exceptions import UserError
from utils.tagtools import translateTagsToPreferredLanguage

from init import rdb
from bson import ObjectId
import redis_lock
from config import VideoConfig, TagsConfig
from services.getVideo import getVideoDetailWithTagObjects

@usingResource('tags')
def editVideoTags(vid, tags, user):
    if len(tags) > VideoConfig.MAX_TAGS_PER_VIDEO :
        raise UserError('TAGS_LIMIT_EXCEEDED')
    tagdb.verify_tags(tags)
    tags = tagdb.translate_tags(tags)
    tags = list(set(tags))
    item = tagdb.db.items.find_one({'_id': ObjectId(vid)})
    if item is None:
        raise UserError('ITEM_NOT_EXIST')
    if len(tags) > VideoConfig.MAX_TAGS_PER_VIDEO:
        raise UserError('TOO_MANY_TAGS')
    with redis_lock.Lock(rdb, "videoEdit:" + item['item']['unique_id']), MongoTransaction(client) as s :
        tagdb.update_item_tags(item, tags, makeUserMeta(user), s())
        s.mark_succeed()

def getVideoTags(vid, user_language) :
    _, tag_objs = getVideoDetailWithTagObjects(vid)
    return translateTagsToPreferredLanguage(tag_objs, user_language)

