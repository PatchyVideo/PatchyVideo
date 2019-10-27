
from db import tagdb as db
from bson import ObjectId

def getVideoDetail(id):
    return db.retrive_item({'_id': ObjectId(id)})

def getTagCategories(tags) :
    return db.get_tag_category(tags)

def getTagCategoryMap(tags) :
    return db.get_tag_category_map(tags)
