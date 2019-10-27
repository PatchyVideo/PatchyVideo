
import time

from flask import render_template, request, jsonify, redirect, session

from main import app
from utils.interceptors import loginOptional, loginRequired
from utils.html import buildPageSelector
from services.playlist import *

@app.route('/lists', methods = ['POST', 'GET'])
@loginOptional
def pages_playlists_list(rd, user):
    rd.page = int(request.values['page'] if 'page' in request.values else 1)
    rd.search_term = request.values['q'] if 'q' in request.values else ''
    rd.page_size = int(request.values['page_size'] if 'page_size' in request.values else 20)
    rd.order = "latest"
    query_obj = {}
    if rd.search_term :
        query_obj = {'$or':[{'title.english': {'$regex': rd.search_term}}, {'desc.english': {'$regex': rd.search_term}}]}
    _, playlists = listPlaylists(rd.page - 1, rd.page_size, query_obj, rd.order)
    playlists_count = playlists.count()
    rd.lists = [i for i in playlists]
    rd.count = playlists_count
    rd.page_count = (playlists_count - 1) // rd.page_size + 1
    rd.page_selector_text = buildPageSelector(rd.page, rd.page_count, lambda a: 'javascript:gotoPage(%d);'%a)
    return 'content_playlists_list.html'


