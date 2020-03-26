
from db import tagdb as db
from bson import ObjectId
from utils.exceptions import UserError
from services.tcb import filterSingleVideo

def getVideoDetail(vid, user, raise_error = False):
	return filterSingleVideo(vid, user, raise_error)

def getVideoDetailWithTags(vid, language, user) :
	video_obj = filterSingleVideo(vid, user)
	return db.retrive_item_with_tag_category_map(video_obj, language)

def getTagCategoryMap(tags) :
	return db.get_tag_category_map(tags)

def getVideoDetailNoFilter(vid):
	return db.retrive_item(vid)

