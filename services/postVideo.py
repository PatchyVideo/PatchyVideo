
import os
import time
from init import app, rdb
from utils.jsontools import *
from utils.dbtools import makeUserMeta, MongoTransaction
from utils.crypto import random_bytes_str
from utils.http import clear_url

from spiders import dispatch
from db import tagdb, db, client

from bson import ObjectId

import traceback
from services.playlist import addVideoToPlaylist, insertIntoPlaylist
from PIL import Image, ImageSequence
import requests
import io

import redis_lock
from config import VideoConfig

_COVER_PATH = os.getenv('IMAGE_PATH', "/images") + "/covers/"

def _gif_thumbnails(frames):
	for frame in frames:
		thumbnail = frame.copy()
		thumbnail.thumbnail((320, 200), Image.ANTIALIAS)
		yield thumbnail

def _make_video_data(data, copies, playlists, url) :
	filename = ""
	for _ in range(3) :
		try :
			r = requests.get(data['thumbnailURL'])
			if r.status_code == 200 :
				img = Image.open(io.BytesIO(r.content))
				if data['thumbnailURL'][-4:].lower() == '.gif' :
					filename = random_bytes_str(24) + ".gif"
					frames = ImageSequence.Iterator(img)
					frames = _gif_thumbnails(frames)
					om = next(frames) # Handle first frame separately
					om.info = img.info # Copy sequence info
					om.save(_COVER_PATH + filename, save_all = True, append_images = list(frames), loop = 0)
				else :
					filename = random_bytes_str(24) + ".png"
					img.thumbnail((320, 200), Image.ANTIALIAS)
					img.save(_COVER_PATH + filename)
				break
		except :
			continue
	return {
		"url": url,
		"title": data['title'],
		"desc": data['desc'],
		"thumbnail_url": data['thumbnailURL'],
		"cover_image": filename,
		'site': data['site'],
		"unique_id": data['unique_id'],
		'series': playlists,
		'copies': copies,
		'upload_time': data['uploadDate'],
		'views': -1,
		'rating': -1.0
	}

def getAllcopies(vid, session) :
	if not vid :
		return []
	this_video = tagdb.retrive_item({"_id": ObjectId(vid)}, session = session)
	if this_video is None :
		return []
	copies = this_video['item']['copies']
	# add self
	copies.append(ObjectId(vid))
	# use set to remove duplicated items
	return list(set(copies))

def addThiscopy(dst_vid, this_vid, session):
	if this_vid is None :
		return
	dst_video = tagdb.retrive_item({"_id": ObjectId(dst_vid)}, session = session)
	if dst_video is None :
		return
	dst_copies = dst_video['item']['copies']
	if isinstance(this_vid, list) :
		dst_copies.extend(this_vid)
	else :
		dst_copies.append(ObjectId(this_vid))
	dst_copies = list(set(dst_copies) - set([ObjectId(dst_vid)]))
	tagdb.update_item_query(dst_vid, {"$set": {"item.copies": dst_copies}}, session = session)

def postVideo(url, tags, parsed, dst_copy, dst_playlist, dst_rank, user):
	print('Adding %s with copies %s to playlist %s' % (url, dst_copy or '<None>', dst_playlist or '<None>'))
	try :
		ret = parsed.get_metadata(parsed, url)
		if ret["status"] == 'failed' :
			return "FETCH_FAILED", ret
		if hasattr(parsed, 'LOCAL_SPIDER') :
			url = ret["data"]["url"]
		else :
			url = clear_url(url)
		lock_id = "videoEdit:" + ret["data"]["unique_id"]
		with redis_lock.Lock(rdb, lock_id) :
			unique, conflicting_item = verifyUniqueness(ret["data"]["unique_id"])
			playlists = []
			dst_rank = -1 if dst_rank is None else dst_rank
			#playlist_lock = None
			if dst_playlist :
				#playlist_lock = redis_lock.Lock(rdb, "playlistEdit:" + str(dst_playlist))
				#playlist_lock.acquire()
				if db.playlists.find_one({'_id': ObjectId(dst_playlist)}) is not None :
					playlists = [ ObjectId(dst_playlist) ]
			if not unique:
				print('Video already exist as %s' % ret["data"]["unique_id"])

				"""
				Update existing video
				"""
				# new field: uploadDate
				if 'upload_time' not in conflicting_item['item'] or conflicting_item['item']['upload_time'] == '' or conflicting_item['item']['site'] == 'youtube':
					upload_time = ret['data']['uploadDate']
					with MongoTransaction(client) as s :
						tagdb.update_item_query(conflicting_item['_id'], {'$set': {'item.upload_time': upload_time}}, session = s())
						s.mark_succeed()
					if not tags :
						return 'SUCCEED', conflicting_item['_id']

				if conflicting_item['item']['site'] == 'nicovideo':
					desc = ret['data']['desc']
					with MongoTransaction(client) as s :
						tagdb.update_item_query(conflicting_item['_id'], {'$set': {'item.desc': desc}}, session = s())
						s.mark_succeed()
					if not tags :
						return 'SUCCEED', conflicting_item['_id']

				# this video already exist in the database
				# if the operation is to add a link to other copies and not adding self
				if dst_copy and dst_copy != conflicting_item['_id'] :
					print('Adding to to copies')
					with redis_lock.Lock(rdb, 'editLink'), MongoTransaction(client) as s :
						print('Adding to to copies, lock acquired')
						# find all copies of video dst_copy, self included
						all_copies = getAllcopies(dst_copy, session = s())
						# find all videos linked to source video
						all_copies += getAllcopies(conflicting_item['_id'], session = s())
						# remove duplicated items
						all_copies = list(set(all_copies))
						# add this video to all other copies found
						if len(all_copies) <= VideoConfig.MAX_COPIES :
							for dst_vid in all_copies :
								addThiscopy(dst_vid, all_copies, session = s())
							print('Successfully added to copies')
							s.mark_succeed()
						else :
							#if playlist_lock :
							#    playlist_lock.release()
							print('TOO_MANY_COPIES')
							return "TOO_MANY_COPIES", {}
				# if the operation is adding this video to playlist
				if dst_playlist :
					print('Adding to playlist at position %d' % dst_rank)
					if dst_rank == -1 :
						addVideoToPlaylist(dst_playlist, conflicting_item['_id'], user)
					else :
						insertIntoPlaylist(dst_playlist, conflicting_item['_id'], dst_rank, user)
				# merge tags
				with MongoTransaction(client) as s :
					print('Merging tags')
					tagdb.update_item_tags_merge(conflicting_item['_id'], tags, makeUserMeta(user), session = s())
					s.mark_succeed()
				#if playlist_lock :
				#    playlist_lock.release()
				#return "VIDEO_ALREADY_EXIST", conflicting_item['_id']
				return "SUCCEED", conflicting_item['_id']
			else :
				# expand dst_copy to all copies linked to dst_copy
				if dst_copy :
					print('Adding to to copies')
					with redis_lock.Lock(rdb, 'editLink'), MongoTransaction(client) as s :
						print('Adding to to copies, lock acquired')
						all_copies = getAllcopies(dst_copy, session = s())
						new_item_id = tagdb.add_item(tags, _make_video_data(ret["data"], all_copies, playlists, url), makeUserMeta(user), session = s())
						all_copies.append(ObjectId(new_item_id))
						if len(all_copies) <= VideoConfig.MAX_COPIES :
							for dst_vid in all_copies :
								addThiscopy(dst_vid, all_copies, session = s())
							print('Successfully added to copies')
							s.mark_succeed()
						else :
							#if playlist_lock :
							#    playlist_lock.release()
							print('TOO_MANY_COPIES')
							return "TOO_MANY_COPIES", {}
				else :
					with MongoTransaction(client) as s :
						new_item_id = tagdb.add_item(tags, _make_video_data(ret["data"], [], playlists, url), makeUserMeta(user), session = s())
						print('New video added to database')
						s.mark_succeed()
				# if the operation is adding this video to playlist
				if dst_playlist :
					print('Adding to playlist at position %d' % dst_rank)
					if dst_rank == -1 :
						addVideoToPlaylist(dst_playlist, new_item_id, user)
					else :
						insertIntoPlaylist(dst_playlist, new_item_id, dst_rank, user)
				#if playlist_lock :
				#    playlist_lock.release()
				print('SUCCEED')
				return 'SUCCEED', new_item_id
	except :
		print('****Exception!')
		print(traceback.format_exc())
		try :
			problematic_lock = redis_lock.Lock(rdb, 'editLink')
			problematic_lock.reset()
		except:
			pass
		return "UNKNOWN", traceback.format_exc()

def verifyUniqueness(postingId):
	val = tagdb.retrive_item({"item.unique_id": postingId})
	return val is None, val

def verifyTags(tags):
	return tagdb.verify_tags([tag.strip() for tag in tags])
