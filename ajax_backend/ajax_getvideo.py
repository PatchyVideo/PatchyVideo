import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session, abort

from init import app
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError

from spiders import dispatch

from services.getVideo import getVideoDetail, getVideoDetailWithTags
from services.playlist import listPlaylistsForVideo
from config import TagsConfig, VideoConfig


@app.route('/getvideo.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_getvideo(rd, user, data):
	vidid = data.vid
	try:
		obj, tags, category_tag_map, tag_category_map = getVideoDetailWithTags(vidid, 'CHS')
	except UserError:
		abort(404)

	tag_by_category = category_tag_map
	for category in tag_by_category :
		tag_by_category[category] = list(sorted(tag_by_category[category]))
	copies = []
	for item in obj['item']['copies'] :
		ver = getVideoDetail(item)
		assert ver
		copies.append(ver)
	playlists = listPlaylistsForVideo(vidid)

	return "json", makeResponseSuccess({
		"video" : obj,
		"tags" : tags,
		"copies" : copies,
		"playlists" : playlists,
		"tag_by_category": tag_by_category
	})

