
from db import tagdb as db
from bson import ObjectId
from utils.exceptions import UserError

def getVideoDetail(id):
    return db.retrive_item({'_id': ObjectId(id)})

def getVideoDetailWithTagObjects(id) :
    obj = db.retrive_item({'_id': ObjectId(id)})
    if obj :
        tags = [tag for tag in db.db.tags.find({'tag': {'$in': obj['tags']}})]
        return obj, tags
    raise UserError('ITEM_NOT_EXIST')

def getTagCategories(tags) :
    return db.get_tag_category(tags)

def getTagCategoryMap(tags) :
    return db.get_tag_category_map(tags)
