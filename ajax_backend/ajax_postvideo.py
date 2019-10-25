
import time
import os
import redis
from rq import Queue, Connection

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *

from spiders import dispatch
from services.postVideo import postVideo, verifyTags

if os.getenv("USE_RQ", "true") == "true" :
    USE_RQ = True
    from worker import conn
else :
    USE_RQ = False

if USE_RQ :
    print('Using RQ')
    @app.route('/postvideo.do', methods = ['POST'])
    @loginRequiredJSON
    @jsonRequest
    def ajax_postvideo_do(rd, user, data):
        if len(data.url) > 500 :
            return "json", makeResponseFailed("URL too long")
        if len(data.tags) > 200 :
            return "json", makeResponseFailed("Too many tags, max 200 tags per video")
        for tag in data.tags :
            if len(tag) > 48 :
                return "json", makeResponseFailed("Tag length too large(48 characters max)")
        obj, cleanURL = dispatch(data.url)
        if obj is None:
            return "json", makeResponseFailed("Unsupported website")
        tags_ret, unrecognized_tag = verifyTags(data.tags)
        dst_copy = data.copy if 'copy' in data.__dict__ else ''
        dst_playlist = data.pid if 'pid' in data.__dict__ else ''
        dst_rank = data.rank if 'rank' in data.__dict__ else -1
        if tags_ret == 'TAG_NOT_EXIST':
            return "json", makeResponseFailed("Tag %s not recognized" % unrecognized_tag)
        q = Queue(connection = conn)
        task = q.enqueue(postVideo, cleanURL, data.tags, obj, dst_copy, dst_playlist, dst_rank, user)
        ret = makeResponseSuccess({
            "task_id": task.get_id()
        })
        return "json", ret

    @app.route('/postvideo_batch.do', methods = ['POST'])
    @loginRequiredJSON
    @jsonRequest
    def ajax_postvideo_batch_do(rd, user, data):
        if len(data.videos) < 1 :
            return "json", makeResponseFailed("Please post at least 1 video")
        if len(data.videos) > 100 :
            return "json", makeResponseFailed("Too many videos, max 100 per post")
        if len(data.tags) > 200 :
            return "json", makeResponseFailed("Too many tags, max 200 tags per video")
        for tag in data.tags :
            if len(tag) > 48 :
                return "json", makeResponseFailed("Tag length too large(48 characters max)")
        tags_ret, unrecognized_tag = verifyTags(data.tags)
        dst_copy = data.copy if 'copy' in data.__dict__ and data.copy is not None else ''
        dst_playlist = data.pid if 'pid' in data.__dict__ and data.pid is not None else ''
        dst_rank = int(data.rank if 'rank' in data.__dict__ and data.rank is not None else -1)
        if tags_ret == 'TAG_NOT_EXIST':
            return "json", makeResponseFailed("Tag %s not recognized" % unrecognized_tag)
        succeed = True
        q = Queue(connection = conn)
        for idx, url in enumerate(data.videos) :
            obj, cleanURL = dispatch(url)
            if obj is None:
                succeed = False
            next_idx = idx if dst_rank >= 0 else 0
            task = q.enqueue(postVideo, cleanURL, data.tags, obj, dst_copy, dst_playlist, dst_rank + next_idx, user)
        if succeed :
            ret = makeResponseSuccess({
                "task_id": task.get_id()
            })
        else :
            ret =  makeResponseFailed("Unsupported website")
        return "json", ret
else :
    print('Not using RQ')
    @app.route('/postvideo.do', methods = ['POST'])
    @loginRequiredJSON
    @jsonRequest
    def ajax_postvideo_do(rd, user, data):
        print('post video')
        if len(data.url) > 500 :
            return "json", makeResponseFailed("URL too long")
        if len(data.tags) > 200 :
            return "json", makeResponseFailed("Too many tags, max 200 tags per video")
        for tag in data.tags :
            if len(tag) > 48 :
                return "json", makeResponseFailed("Tag length too large(48 characters max)")
        obj, cleanURL = dispatch(data.url)
        if obj is None:
            return "json", makeResponseFailed("Unsupported website")
        print('post video preliminary check completed')
        tags_ret, unrecognized_tag = verifyTags(data.tags)
        dst_copy = data.copy if 'copy' in data.__dict__ else ''
        dst_playlist = data.pid if 'pid' in data.__dict__ else ''
        dst_rank = data.rank if 'rank' in data.__dict__ else -1
        if tags_ret == 'TAG_NOT_EXIST':
            return "json", makeResponseFailed("Tag %s not recognized" % unrecognized_tag)
        print('post video tag check completed')
        result_msg, result_id = postVideo(cleanURL, data.tags, obj, dst_copy, dst_playlist, dst_rank, user)
        if result_msg == "SUCCEESS" :
            print('post video SUCCEESS')
            ret = makeResponseFailed("operation succeed, last video_id=%s" % str(result_id))
        else :
            print('post video %s'%result_msg)
            ret =  makeResponseFailed("operation failed, last err_code=%s" % result_msg)
        return "json", ret


    @app.route('/postvideo_batch.do', methods = ['POST'])
    @loginRequiredJSON
    @jsonRequest
    def ajax_postvideo_batch_do(rd, user, data):
        if len(data.videos) < 1 :
            return "json", makeResponseFailed("Please post at least 1 video")
        if len(data.videos) > 100 :
            return "json", makeResponseFailed("Too many videos, max 100 per post")
        if len(data.tags) > 200 :
            return "json", makeResponseFailed("Too many tags, max 200 tags per video")
        for tag in data.tags :
            if len(tag) > 48 :
                return "json", makeResponseFailed("Tag length too large(48 characters max)")
        tags_ret, unrecognized_tag = verifyTags(data.tags)
        dst_copy = data.copy if 'copy' in data.__dict__ and data.copy is not None else ''
        dst_playlist = data.pid if 'pid' in data.__dict__ and data.pid is not None else ''
        dst_rank = int(data.rank if 'rank' in data.__dict__ and data.rank is not None else -1)
        if tags_ret == 'TAG_NOT_EXIST':
            return "json", makeResponseFailed("Tag %s not recognized" % unrecognized_tag)
        succeed = True
        for idx, url in enumerate(data.videos) :
            obj, cleanURL = dispatch(url)
            if obj is None:
                succeed = False
            next_idx = idx if dst_rank >= 0 else 0
            result_msg, result_id = postVideo(cleanURL, data.tags, obj, dst_copy, dst_playlist, dst_rank + next_idx, user)
            if result_msg != "SUCCEED" :
                succeed = False
        if succeed :
            ret = makeResponseFailed("operation succeed, last video_id=%s" % str(result_id))
        else :
            ret =  makeResponseFailed("operation failed, last err_code=%s" % result_msg)
        return "json", ret
