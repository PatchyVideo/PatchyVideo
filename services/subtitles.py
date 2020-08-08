
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
from config import Subtitles

from googletrans import Translator
translator = Translator()

import webvtt
import io

import redis_lock

VALID_SUBTITLE_FORMAT = [
	'srt',
	'vtt',
	'ass'
]

def getSubtitle(subid: ObjectId) :
	sub_item = db.subtitles.find_one({'_id': subid})
	if sub_item is None :
		raise UserError('ITEM_NOT_FOUND')
	if sub_item['deleted'] :
		raise UserError('ITEM_NOT_FOUND')
	del sub_item['deleted']
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
	try :
		size = len(content.encode('utf-8'))
	except :
		size = -1
	filterOperation('postSubtitle', user)
	with redis_lock.Lock(rdb, "videoEdit:" + video_item['item']['unique_id']), MongoTransaction(client) as s :
		existing_item = db.subtitles.find_one({'vid': vid, 'lang': language, 'format': subformat, 'meta.created_by': makeUserMeta(user)}, session = s())
		if existing_item is None :
			subid = db.subtitles.insert_one({
				'vid': vid,
				'lang': language,
				'format': subformat,
				'content': content,
				'size': size,
				'deleted': False,
				'autogen': False,
				'version': 0,
				'meta': makeUserMetaObject(user)
			}, session = s()).inserted_id
		else :
			db.subtitles.update_one({'_id': existing_item['_id']}, {
				'$set': {
					'content': content,
					'size': size,
					'meta.modified_at': datetime.utcnow()
				}
			}, session = s())
			subid = existing_item['_id']
		s.mark_succeed()
		return ObjectId(subid)

def updateSubtitleMeta(user, subid: ObjectId, language: str, subformat: str) :
	if language not in VALID_LANGUAGES :
		raise UserError('INVALID_LANGUAGE')
	subformat = subformat.lower()
	if subformat not in VALID_SUBTITLE_FORMAT :
		raise UserError('INVALID_SUBTITLE_FORMAT')
	with MongoTransaction(client) as s :
		sub_obj = db.subtitles.find_one({'_id': subid}, session = s())
		if sub_obj is None :
			raise UserError('ITEM_NOT_FOUND')
		filterOperation('updateSubtitleMeta', user, sub_obj)
		db.subtitles.update_one({'_id': subid}, {'$set': {
			'format': subformat,
			'lang': language,
			'meta.modified_at': datetime.utcnow(),
			'meta.modified_by': makeUserMeta(user)
		}}, session = s())
		s.mark_succeed()

def updateSubtitleContent(user, subid: ObjectId, content: str) :
	try :
		size = len(content.encode('utf-8'))
	except :
		size = -1
	with MongoTransaction(client) as s :
		sub_obj = db.subtitles.find_one({'_id': subid}, session = s())
		if sub_obj is None :
			raise UserError('ITEM_NOT_FOUND')
		filterOperation('updateSubtitleContent', user, sub_obj)
		db.subtitles.update_one({'_id': subid}, {'$set': {
			'content': content,
			'size': size,
			'meta.modified_at': datetime.utcnow(),
			'meta.modified_by': makeUserMeta(user)
		}}, session = s())
		s.mark_succeed()

def deleteSubtitle(user, subid: ObjectId) :
	with MongoTransaction(client) as s :
		sub_obj = db.subtitles.find_one({'_id': subid}, session = s())
		if sub_obj is None :
			raise UserError('ITEM_NOT_FOUND')
		filterOperation('deleteSubtitle', user, sub_obj)
		db.subtitles.update_one({'_id': subid}, {'$set': {
			'deleted': True,
			'meta.modified_at': datetime.utcnow(),
			'meta.modified_by': makeUserMeta(user)
		}}, session = s())
		s.mark_succeed()

def listVideoSubtitles(vid: ObjectId) :
	items = list(db.subtitles.aggregate([
		{'$match': {'vid': vid, 'deleted': False}},
		{'$lookup': {'from': 'users', 'localField': 'meta.created_by', 'foreignField': '_id', 'as': 'user_obj'}},
		{'$project': {'_id': 1, 'lang': 1, 'format': 1, 'meta': 1, 'autogen': 1, 'version': 1, 'size': 1, 'user_obj._id': 1, 'user_obj.profile.username': 1, 'user_obj.profile.image': 1}},
		{'$sort': {"meta.modified_at": -1}}
	]))
	return items
	
def translateVTT(subid: ObjectId, language: str) :
	sub_obj = db.subtitles.find_one({'_id': subid})
	if sub_obj is None :
		raise UserError('ITEM_NOT_FOUND')
	if sub_obj['format'] != 'vtt' :
		raise UserError('ONLY_VTT_SUPPORTED')
	vtt = webvtt.read_buffer(io.StringIO(sub_obj['content']))
	l = len(vtt)
	bs = 10
	for i in range(0, l, bs) :
		all_texts = '\n\n\n'.join([vtt[j].text for j in range(i, min(i + bs, l))])
		result = translator.translate(all_texts, dest = language).text.split('\n\n\n')
		for i2, j in enumerate(range(i, min(i + bs, l))) :
			vtt[j].text = result[i2]
	out_file = io.StringIO()
	vtt.write(out_file)
	return out_file.getvalue()

"""
1.1:
Subtitle OCR Request Status for a given video:
	1. NoRecord
	2. Queuing
	3. Reserved // after queryAndProcessQueuingRequests
	4. PendingDownload // OCR program's ACK to us
	5. Downloading // downloading
	6. PendingProcess // downloaded, pending OCR
	7. Processing // OCR running
	8. RecordExists // OCR done, maybe out of date if MMDOCR is updated
	9. RecordOutOfDate // video is updated, need re-OCR
	10. Error // worker failed
One can request re-OCR if video is update(determined by admin) or MMD-OCR is updated(by keeping track of a version)
"""

"""
1.2:
Collection subtitle_ocr:
{
	"_id": ...,
	"vid": ObjectId(...),
	"status": "", // described in (1.1)
	"version": 1, // currently 1
	"worker_id": "",
	"meta": ...
}
"""

"""
Each worker has an unique id which is given to authorized cloud computing instances.
Each worker also has an unique private key, all data from worker must be signed
Verifying is done using an interceptor, not here
"""

# client side subtitle OCR services
def requestSubtitleOCR(user, vid: ObjectId) :
	# step 1: verify user and video
	filterOperation('requestSubtitleOCR', user)
	video_item = tagdb.retrive_item(vid)
	if video_item is None :
		raise UserError('VIDEO_NOT_FOUND')
	# step 2: check if request exists
	with redis_lock.Lock(rdb, "videoEdit:" + video_item['item']['unique_id']), redis_lock.Lock(rdb, "mmdocr_global_lock"), MongoTransaction(client) as s :
		ocr_record = db.subtitle_ocr.find_one({"vid": vid}, session = s())
		if ocr_record is None :
			# create new record
			record = {
				"vid": vid,
				"status": "Queuing",
				"version": 0, # version is set in postSubtitleOCRResult
				"worker_id": "", # worker_id is set in queryAndProcessQueuingRequests
				"meta": makeUserMetaObject(user)
			}
			db.subtitle_ocr.insert_one(record, session = s())
		else :
			status = ocr_record['status']
			record_id = ocr_record['_id']
			record_version = ocr_record['version']
			mmdocr_version = int(Config.MMDOCR_VERSION)
			if status in ['NoRecord', 'RecordOutOfDate'] :
				assert status != "NoRecord"
				db.subtitle_ocr.update_one({"_id": record_id}, {"$set": {
					"status": "Queuing",
					"meta.modified_at": datetime.utcnow(),
					"meta.modified_by": ObjectId(user['_id'])
				}}, session = s())
				pass
			elif status == 'RecordExists' :
				if record_version < mmdocr_version :
					# newer version of mmdocr exists
					db.subtitle_ocr.update_one({"_id": record_id}, {"$set": {
						"status": "Queuing",
						"meta.modified_at": datetime.utcnow(),
						"meta.modified_by": ObjectId(user['_id'])
					}}, session = s())
					pass
				else :
					raise UserError('RECORD_ALREADY_EXISTS')
			else :
				raise UserError('VIDEO_BEING_PROCESSED')
		s.mark_succeed()

def querySubtitleOCRStatus(vid: ObjectId) :
	# step 1: verify video
	video_item = tagdb.retrive_item(vid)
	if video_item is None :
		raise UserError('VIDEO_NOT_FOUND')
	with redis_lock.Lock(rdb, "mmdocr_global_lock") :
		# step 2: query and return
		ocr_record = db.subtitle_ocr.find_one({"vid": vid})
		if ocr_record is None :
			return "NoRecord"
		else :
			return ocr_record['status']

# server side subtitle OCR services
def queryAndProcessQueuingRequests(user, max_videos: int, worker_id: str) :
	filterOperation('subtitleocr_queryAndProcessQueuingRequests', user)
	# step 1: max_videos > 0 and max_videos <= 100
	if max_videos <= 0 or max_videos > Subtitles.MAX_WORKER_JOBS :
		raise UserError('TOO_MANY_JOBS')
	with redis_lock.Lock(rdb, "mmdocr_global_lock"), MongoTransaction(client) as s :
		# step 2: get top k oldest requests
		ret = list(db.subtitle_ocr.find({"status": "Queuing"}, session = s()).sort([("meta.modified_at", 1)]).limit(max_videos)) # FIFO
		ret_vids = [i['vid'] for i in ret]
		ret_ids = [i['_id'] for i in ret]
		# step 3: retrive video URLs
		video_items = tagdb.retrive_items({"_id": {"$in": ret_vids}}, session = s())
		video_urls = [{"url": i["item"]["url"], "unique_id": i["item"]["unique_id"]} for i in video_items]
		# step 4: mark reserved
		db.subtitle_ocr.update_many({"_id": {"$in": ret_ids}}, {"$set": {"status": "Reserved", "worker_id": worker_id}}, session = s())
		s.mark_succeed()
		# step 5: return
		return video_urls

def updateRequestStatus(user, video_status_map, worker_id: str) : # map of unique_id to status
	filterOperation('subtitleocr_updateRequestStatus', user)
	with redis_lock.Lock(rdb, "mmdocr_global_lock"), MongoTransaction(client) as s :
		for unqiue_id, status in video_status_map.items() :
			if status not in ['PendingDownload', 'Downloading', 'PendingProcess', 'Processing', 'Error', 'Queuing'] :
				continue
			# step 1: verify videos
			video_item = tagdb.retrive_item({"item.unique_id": unqiue_id}, session = s())
			if video_item is not None :
				# step 2: update
				db.subtitle_ocr.update_one({"vid": video_item['_id']}, {"$set": {"status": status, "worker_id": worker_id}}, session = s())
		s.mark_succeed()

def postSubtitleOCRResult(user, unique_id: str, content: str, subformat: str, version: int, worker_id: str) :
	# step 1: verify and post
	filterOperation('subtitleocr_postSubtitleOCRResult', user)
	subformat = subformat.lower()
	if subformat not in VALID_SUBTITLE_FORMAT :
		raise UserError('INVALID_SUBTITLE_FORMAT')
	video_item = tagdb.retrive_item({"item.unique_id": unique_id})
	if video_item is None :
		raise UserError('VIDEO_NOT_FOUND')
	try :
		size = len(content.encode('utf-8'))
	except :
		size = -1
	with redis_lock.Lock(rdb, "videoEdit:" + video_item['item']['unique_id']), redis_lock.Lock(rdb, "mmdocr_global_lock"), MongoTransaction(client) as s :
		# delete old versions
		db.subtitles.delete_many({'vid': video_item['_id'], 'autogen': True}, session = s())
		subid = db.subtitles.insert_one({
			'vid': video_item['_id'],
			'lang': 'UNKNOWN',
			'format': subformat,
			'content': content,
			'size': size,
			'deleted': False,
			'version': version,
			'autogen': True,
			'meta': makeUserMetaObject(None)
		}, session = s()).inserted_id
		# step 2: update subtitle_ocr
		db.subtitle_ocr.update_one({"vid": video_item['_id']}, {"$set": {"status": "RecordExists", "version": version, "worker_id": worker_id}}, session = s())
		s.mark_succeed()
		return subid

# admin interface
def listAllPendingRequest(user, order: str, page_idx: int = 0, page_size: int = 30) :
	# list subtitle_ocr with status not in ['NoRecord', 'RecordExists', 'RecordOutOfDate']
	filterOperation('subtitleocr_listAllPendingRequest', user)
	with redis_lock.Lock(rdb, "mmdocr_global_lock") :
		result = db.subtitle_ocr.find({"status": {"$nin": ['NoRecord', 'RecordExists', 'RecordOutOfDate']}})
		if order not in ['latest', 'oldest'] :
			raise UserError('INCORRECT_ORDER')
		if order == 'latest':
			result = result.sort([("meta.created_at", -1)])
		if order == 'oldest':
			result = result.sort([("meta.created_at", 1)])
		result_count = result.count()
		result = [i for i in result.skip(page_idx * page_size).limit(page_size)]
		return result, result_count

def setRequestStatus(user, vid: ObjectId, status: str) :
	filterOperation('subtitleocr_setRequestStatus', user)
	if status not in ['Queuing', 'PendingDownload', 'Downloading', 'PendingProcess', 'Processing', 'NoRecord', 'RecordExists', 'RecordOutOfDate', 'Error'] :
		raise UserError('INCORRECT_STATUS')
	with redis_lock.Lock(rdb, "mmdocr_global_lock") :
		db.subtitle_ocr.update_one({"vid": vid}, {"$set": {"status": status}})

def setAllRequestStatus(user, status: str) :
	# use this in case of any catastrophic failure
	filterOperation('subtitleocr_setAllRequestStatus', user)
	if status not in ['PendingDownload', 'Downloading', 'PendingProcess', 'Processing', 'NoRecord', 'RecordExists', 'RecordOutOfDate'] :
		raise UserError('INCORRECT_STATUS')
	with redis_lock.Lock(rdb, "mmdocr_global_lock") :
		db.subtitle_ocr.update_many({}, {"$set": {"status": status}})
