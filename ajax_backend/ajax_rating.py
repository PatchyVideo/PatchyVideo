
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest, loginRequiredJSON, loginOptional
from utils.jsontools import *
from utils.exceptions import UserError
from utils import getDefaultJSON

from services.rating import rateVideo, ratePlaylist, getVideoRating, getPlaylistRating, getVideoRatingAggregate, getPlaylistRatingAggregate
from services.tcb import filterOperation

from bson import ObjectId

@app.route('/rating/video.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rating_video(rd, user, data):
	rateVideo(user, ObjectId(data.vid), data.stars)

@app.route('/rating/playlist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rating_playlist(rd, user, data):
	ratePlaylist(user, ObjectId(data.pid), data.stars)

@app.route('/rating/get_video.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rating_get_video(rd, user, data):
	user_rating, (total_rating, total_user) = getVideoRating(user, ObjectId(data.vid))
	return "json", makeResponseSuccess({'user_rating': user_rating, 'total_rating': total_rating, 'total_user': total_user})

@app.route('/rating/get_playlist.do', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_rating_get_playlist(rd, user, data):
	user_rating, (total_rating, total_user) = getPlaylistRating(user, ObjectId(data.pid))
	return "json", makeResponseSuccess({'user_rating': user_rating, 'total_rating': total_rating, 'total_user': total_user})

@app.route('/rating/get_video_total.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_rating_get_video_total(rd, user, data):
	total_rating, total_user = getVideoRatingAggregate(ObjectId(data.vid))
	return "json", makeResponseSuccess({'total_rating': total_rating, 'total_user': total_user})

@app.route('/rating/get_playlist_total.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_rating_get_playlist_total(rd, user, data):
	total_rating, total_user = getPlaylistRatingAggregate(ObjectId(data.pid))
	return "json", makeResponseSuccess({'total_rating': total_rating, 'total_user': total_user})

