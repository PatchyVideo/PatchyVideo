
import redis_lock

from bson import ObjectId

from init import rdb
from db import db, client
from utils.dbtools import MongoTransaction
from utils.exceptions import UserError
from utils.dbtools import makeUserMetaObject
from services.tcb import filterOperation
from config import Comments

"""
Standalone comment APIs
"""

"""
Comments are grouped in to threads, each object(video/user/playlist) can only have up to one thread associated with it
a comment contains:
comment: {
    "thread": thread id
    "content": comment content,
    "meta" : {
        ...
    },
    "hidden": not shown by default,
    "deleted": you cannot see this,
    "upvotes",
    "downvotes"
}
a sub comment contains:
sub_comment: {
    "parent": parent comment id,
    "reply_to": reply to comment id,
    "content": comment content,
    "meta" : {
        ...
    }
    "hidden": not shown by default,
    "deleted": you cannot see this,
    "upvotes",
    "downvotes"
}
"""

def createThread(owner : ObjectId, session = None) : # thread is created by the website automatically, not user
    # owner is an user id, who will receive notification if new comment was added
    tid = db.comment_threads.insert_one({'count': 0, 'owner': owner}, session = session).inserted_id
    return ObjectId(tid)

def addComment(user, thread_id : ObjectId, text : str) : # user can add comments
    # TODO notify user being replied to
    filterOperation('postComment', user)
    l = len(text)
    if l > Comments.MAX_COMMENT_LENGTH_LONG :
        raise UserError('COMMENT_TOO_LONG')
    elif l > Comments.MAX_COMMENT_LENGTH_REGULAR and not filterOperation('postLongComment', user, raise_exception = False) :
        raise UserError('COMMENT_TOO_LONG')
    thread_obj = db.comment_threads.find_one({'_id': thread_id})
    if thread_obj is None :
        raise UserError('THREAD_NOT_EXIST')
    with redis_lock.Lock(rdb, "thread:" + str(thread_id)), MongoTransaction(client) as s :
        cid = str(db.comment_items.insert_one({
            'thread': thread_id,
            'content': text,
            'hidden': False,
            'deleted': False,
            'upvotes': 0,
            'downvotes': 0,
            'meta': makeUserMetaObject(user)
        }, session = s()).inserted_id)
        db.comment_threads.update_one({'_id': thread_id}, {'$inc': {'count': int(1)}}, session = s())
        s.mark_succeed()
        return cid

def addReply(user, reply_to : ObjectId, text : str) : # user can add comments
    """
    reply_to: comment id
    """
    filterOperation('postComment', user)
    # TODO notify user being replied to
    l = len(text)
    if l > Comments.MAX_COMMENT_LENGTH_LONG :
        raise UserError('COMMENT_TOO_LONG')
    elif l > Comments.MAX_COMMENT_LENGTH_REGULAR and not filterOperation('postLongComment', user, raise_exception = False) :
        raise UserError('COMMENT_TOO_LONG')
    parent_obj = db.comment_items.find_one({'_id': reply_to})
    if parent_obj is None :
        raise UserError('PARENT_NOT_EXIST')
    with MongoTransaction(client) as s :
        if 'thread' in parent_obj : # reply to primary comment
            db.comment_items.insert_one({
                'parent': reply_to,
                'content': text,
                'hidden': False,
                'deleted': False,
                'upvotes': 0,
                'downvotes': 0,
                'meta': makeUserMetaObject(user)
            }, session = s())
        else : # reply to secondary comment
            db.comment_items.insert_one({
                'parent': parent_obj['parent'],
                'reply_to': reply_to,
                'content': text,
                'hidden': False,
                'deleted': False,
                'upvotes': 0,
                'downvotes': 0,
                'meta': makeUserMetaObject(user)
            }, session = s())
        s.mark_succeed()

def hideComment(user, comment_id : ObjectId) :
    pass

def delComment(user, comment_id : ObjectId) :
    pass

def listThread(thread_id : ObjectId) :
    if db.comment_threads.find_one({'_id': thread_id}) is None :
        raise UserError('THREAD_NOT_EXIST')
    ret = list(db.comment_items.aggregate([
        {'$match': {'thread': thread_id}},
        {'$lookup': {'from': 'comment_items', 'localField': '_id', 'foreignField': 'parent', 'as': 'children'}}
    ]))
    users = []
    for comment in ret :
        users.append(comment['meta']['created_by'])
        for child in comment['children'] :
            users.append(child['meta']['created_by'])
    users = db.users.aggregate([
        {'$match': {'_id': {'$in': users}}},
        {'$project': {'profile.username': 1, 'profile.desc': 1, 'profile.image': 1}}
    ])
    return list(ret), list(users)

def addToVideo(user, vid : ObjectId, text : str) :
    filterOperation('postComment', user)
    video_obj = db.items.find_one({'_id': vid})
    if video_obj is None :
        raise UserError('VIDEO_NOT_EXIST')
    with redis_lock.Lock(rdb, "videoEdit:" + video_obj["item"]["unique_id"]) :
        if 'comment_thread' in video_obj :
            cid = addComment(user, video_obj['comment_thread'], text)
            return video_obj['comment_thread'], cid
        else :
            with MongoTransaction(client) as s :
                tid = createThread(video_obj['meta']['created_by'], session = s())
                db.items.update_one({'_id': vid}, {'$set': {'comment_thread': tid}})
                s.mark_succeed()
            cid = addComment(user, tid, text)
            return tid, cid
    
def addToPlaylist(user, pid : ObjectId, text : str) :
    filterOperation('postComment', user)
    playlist_obj = db.playlists.find_one({'_id': pid})
    if playlist_obj is None :
        raise UserError('PLAYLIST_NOT_EXIST')
    with redis_lock.Lock(rdb, "playlistEdit:" + str(pid)) :
        if 'comment_thread' in playlist_obj :
            cid = addComment(user, playlist_obj['comment_thread'], text)
            return playlist_obj['comment_thread'], cid
        else :
            with MongoTransaction(client) as s :
                tid = createThread(playlist_obj['meta']['created_by'], session = s())
                db.playlists.update_one({'_id': pid}, {'$set': {'comment_thread': tid}})
                s.mark_succeed()
            cid = addComment(user, tid, text)
            return tid, cid

def addToUser(user, uid : ObjectId, text : str) :
    filterOperation('postComment', user)
    user_obj = db.users.find_one({'_id': uid})
    if user_obj is None :
        raise UserError('USER_NOT_EXIST')
    with redis_lock.Lock(rdb, "userEdit:" + str(uid)) :
        if 'comment_thread' in user_obj :
            cid = addComment(user, user_obj['comment_thread'], text)
            return user_obj['comment_thread'], cid
        else :
            with MongoTransaction(client) as s :
                tid = createThread(uid, session = s())
                db.users.update_one({'_id': uid}, {'$set': {'comment_thread': tid}})
                s.mark_succeed()
            cid = addComment(user, tid, text)
            return tid, cid
