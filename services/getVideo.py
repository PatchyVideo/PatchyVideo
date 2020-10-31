
from db import tagdb as db
from bson import ObjectId
from utils.exceptions import UserError
from services.tcb import filterSingleVideo
from scraper.video import dispatch
from utils.logger import log

def getVideoDetail(vid, user, raise_error = False):
	try :
		vid = ObjectId(vid)
	except :
		raise UserError("INCORRECT_VIDEO_ID")
	video_obj = filterSingleVideo(vid, user, raise_error)
	if video_obj is None :
		raise UserError('VIDEO_NOT_EXIST')
	return video_obj

def getVideoDetailWithTags(vid, language, user) :
	try :
		vid = ObjectId(vid)
	except :
		raise UserError("INCORRECT_VIDEO_ID")
	video_obj = filterSingleVideo(vid, user)
	if video_obj is None :
		raise UserError('VIDEO_NOT_EXIST')
	return db.retrive_item_with_tag_category_map(video_obj, language)

def getTagCategoryMap(tags) :
	return db.get_tag_category_map(tags)

def getVideoDetailNoFilter(vid):
	return db.retrive_item(vid)

def getVideoByURL(url) :
	obj, cleanURL = dispatch(url)
	if obj is None:
		log(level = 'WARN', obj = {'url': url})
		raise UserError('UNSUPPORTED_WEBSITE')
	if not cleanURL :
		raise UserError('EMPTY_URL')
	uid = obj.unique_id(obj, cleanURL)
	obj = db.retrive_item({'item.unique_id': uid})
	if obj :
		return obj
	raise UserError('VIDEO_NOT_EXIST')

def getVideosByURLs(urls) :
	ret = []
	for url in urls :
		obj, cleanURL = dispatch(url)
		if obj is None :
			ret.append({'url': url, 'exist': False, 'reason': 'UNSUPPORTED_WEBSITE'})
			continue
		if not cleanURL :
			ret.append({'url': url, 'exist': False, 'reason': 'EMPTY_URL'})
			continue
		uid = obj.unique_id(obj, cleanURL)
		obj = db.retrive_item({'item.unique_id': uid})
		if obj :
			ret.append({'url': url, 'exist': True, 'id': obj['_id']})
		else :
			ret.append({'url': url, 'exist': False, 'reason': 'VIDEO_NOT_EXIST'})
	return ret
