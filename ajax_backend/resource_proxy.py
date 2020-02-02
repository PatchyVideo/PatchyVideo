"""
import requests
import json

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest
from utils.encodings import makeUTF8
from utils.logger import log, beginEvent
from utils.http import getRealIP

@app.route('/proxy', methods = ['GET'])
def ajax_resource_proxy():
	beginEvent('ajax_resource_proxy', getRealIP(request), request.full_path, request.args)
	if not request.args['url'] or not request.args['header']:
		return ""
	url = makeUTF8(request.args['url'])
	header = makeUTF8(json.loads(request.args['header']))
	ret = requests.get(url, headers = header)
	content = ret.content
	log(obj = {'content_length': len(content), 'status_code': ret.status_code})
	return content
	
"""