
import time

from flask import render_template, request, jsonify, redirect, session, abort

from init import app
from utils.interceptors import loginOptional, loginRequired
from utils.html import buildPageSelector
from services.playlist import *
from config import DisplayConfig

@app.route('/lists', methods = ['POST', 'GET'])
@loginOptional
def pages_playlists_list(rd, user):
	rd.page = int(request.values['page'] if 'page' in request.values else 1)
	if rd.page < 1:
		abort(400, 'page must be greater than or equals to 1')
	rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
	if rd.page_size > DisplayConfig.MAX_ITEM_PER_PAGE :
		abort(400, 'Page size too large(max %d videos per page)' % DisplayConfig.MAX_ITEM_PER_PAGE)
	if rd.page_size < 1:
		abort(400, 'Page size must be greater than or equals to 1')
	rd.order = request.values['order'] if 'order' in request.values else 'latest'
	if not rd.order in ['latest', 'oldest']:
		abort(400, 'order must be one of latest,oldest')
	query_obj = {}
	rd.search_term = ''
	if rd.search_term :
		query_obj = {'$or':[{'title.english': {'$regex': rd.search_term}}, {'desc.english': {'$regex': rd.search_term}}]}
	_, playlists, playlists_count = listPlaylists(rd.page - 1, rd.page_size, query_obj, rd.order)
	rd.lists = [i for i in playlists]
	rd.count = playlists_count
	rd.page_count = (playlists_count - 1) // rd.page_size + 1
	rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
	return 'content_playlists_list.html'


