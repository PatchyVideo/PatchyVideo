
from db import tagdb as db
from bson import ObjectId
from utils.exceptions import UserError

def getVideoDetail(id):
	return db.retrive_item({'_id': ObjectId(id)})

def getVideoDetailWithTags(id, language) :
	return db.retrive_item_with_tag_category_map(id, language)

def getTagCategoryMap(tags) :
	return db.get_tag_category_map(tags)


