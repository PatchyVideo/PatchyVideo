
import time
import sys

from flask import render_template, request, jsonify, redirect, session

from init import app, rdb
from utils.interceptors import basePage
from services.listVideo import listVideo, listVideoQuery
from utils.html import buildPageSelector
from bson.json_util import dumps, loads

from config import VideoConfig, PlaylistConfig

@app.route("/postresults/<job_key>", methods=['GET'])
@basePage
def pages_postresult(rd, job_key):
    try :
        job = loads(rdb.get(f'task-{job_key}'))
    except :
        return "data", "No such job"
    if job['finished'] :
        result, obj = job['data']['result'], job['data']['result_obj']
        if result == 'SUCCEED':
            return "redirect", "/video?id=" + str(obj)
        elif result == 'TOO_MANY_COPIES':
            return "data", "Too many copies exist for this video, no more than %d copies of the same video are allowed." % VideoConfig.MAX_COPIES
        elif result == 'VIDEO_ALREADY_EXIST':
            return "data", 'Video already exist, <a href="/video?id=%s">click me</a> to see.' % obj['aux']
        elif result == 'FETCH_FAILED' :
            return "data", "<h1>Failed to fetch video</h1><p>" + obj['data']['exception'] + "</p>"
        elif result == 'UNKNOWN' :
            return "data", obj
        elif result == 'UNAUTHORISED_OPERATION' :
            return "data", "You are not allowed to insert to playlist</br>" + obj
        elif result == 'PLAYLIST_NOT_EXIST' :
            return "data", "playlist no longer exist"
        elif result == 'VIDEO_NOT_EXIST' :
            print('!!!!!VIDEO_NOT_EXIST!!!!!', job, file = sys.stderr)
            return "data", "Contact site admin for help"
        elif result == 'VIDEO_LIMIT_EXCEEDED' :
            return "data", "Too many videos in one playlist, max %d videos per playlist" % PlaylistConfig.MAX_VIDEO_PER_PLAYLIST
        elif result == 'OUT_OF_RANGE' :
            return "data", "insert position out of range"
        return str(job.result), 200
    else:
        return "data", "This post is waiting to be processed, refresh to update."
