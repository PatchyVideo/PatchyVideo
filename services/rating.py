
import redis_lock

from db import db, client
from init import rdb
from bson import ObjectId
from utils.exceptions import UserError
from utils.dbtools import MongoTransaction

def rateVideo(user, vid: ObjectId, stars: int) :
    stars = max(min(int(stars), 10), 1)
    video_obj = db.items.find_one({'_id': vid})
    if video_obj is None :
        raise UserError('VIDEO_NOT_EXIST')
    with redis_lock.Lock(rdb, "videoEdit:" + video_obj["item"]["unique_id"]), MongoTransaction(client) as s :
        rating_obj = db.video_ratings.find_one({'vid': vid, 'uid': ObjectId(user['_id'])}, session = s())
        user_rated = 0
        if rating_obj :
            user_rated = 1
            db.video_ratings.update_one({'vid': vid, 'uid': ObjectId(user['_id'])}, {'$set': {'v': int(stars)}}, session = s())
        else :
            user_rated = 0
            db.video_ratings.insert_one({'vid': vid, 'uid': ObjectId(user['_id']), 'v': int(stars)}, session = s())
        if 'total_rating' in video_obj :
            if rating_obj :
                db.items.update_one({'_id': vid}, {'$inc': {'total_rating': int(stars - rating_obj['v']), 'total_rating_user': int(1 - user_rated)}}, session = s())
            else :
                db.items.update_one({'_id': vid}, {'$inc': {'total_rating': int(stars), 'total_rating_user': int(1 - user_rated)}}, session = s())
        else :
            db.items.update_one({'_id': vid}, {'$set': {'total_rating': int(stars), 'total_rating_user': int(1)}}, session = s())
        s.mark_succeed()

def ratePlaylist(user, pid: ObjectId, stars: int) :
    stars = max(min(int(stars), 10), 1)
    playlist_obj = db.playlists.find_one({'_id': pid})
    if playlist_obj is None :
        raise UserError('PLAYLIST_NOT_EXIST')
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)), MongoTransaction(client) as s :
        rating_obj = db.playlist_ratings.find_one({'pid': pid, 'uid': ObjectId(user['_id'])})
        user_rated = 0
        if rating_obj :
            user_rated = 1
            db.playlist_ratings.update_one({'pid': pid, 'uid': ObjectId(user['_id'])}, {'$set': {'v': int(stars)}}, session = s())
        else :
            user_rated = 0
            db.playlist_ratings.insert_one({'pid': pid, 'uid': ObjectId(user['_id']), 'v': int(stars)}, session = s())
        if 'total_rating' in playlist_obj :
            if rating_obj :
                db.playlists.update_one({'_id': pid}, {'$inc': {'total_rating': int(stars - rating_obj['v']), 'total_rating_user': int(1 - user_rated)}}, session = s())
            else :
                db.playlists.update_one({'_id': pid}, {'$inc': {'total_rating': int(stars), 'total_rating_user': int(1 - user_rated)}}, session = s())
        else :
            db.playlists.update_one({'_id': pid}, {'$set': {'total_rating': int(stars), 'total_rating_user': int(1)}}, session = s())
        s.mark_succeed()

def getVideoRating(user, vid: ObjectId) :
    rating_obj = db.video_ratings.find_one({'vid': vid, 'uid': ObjectId(user['_id'])})
    rating = -1
    if rating_obj :
        rating = rating_obj['v']
    else :
        rating = -1
    return rating, getVideoRatingAggregate(vid)

def getPlaylistRating(user, pid: ObjectId) :
    rating_obj = db.playlist_ratings.find_one({'pid': pid, 'uid': ObjectId(user['_id'])})
    rating = -1
    if rating_obj :
        rating = rating_obj['v']
    else :
        rating = -1
    return rating, getPlaylistRatingAggregate(pid)

def getVideoRatingAggregate(vid: ObjectId) :
    video_obj = db.items.find_one({'_id': vid})
    if video_obj is None :
        raise UserError('VIDEO_NOT_EXIST')
    if 'total_rating' in video_obj :
        return video_obj['total_rating'], video_obj['total_rating_user']
    raise UserError('NOT_RATED')

def getPlaylistRatingAggregate(pid: ObjectId) :
    playlist_obj = db.playlists.find_one({'_id': pid})
    if playlist_obj is None :
        raise UserError('PLAYLIST_NOT_EXIST')
    if 'total_rating' in playlist_obj :
        return playlist_obj['total_rating'], playlist_obj['total_rating_user']
    raise UserError('NOT_RATED')
