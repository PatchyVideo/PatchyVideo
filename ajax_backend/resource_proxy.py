"""
File:
	resource_proxy.py
Location:
	/ajax_backend/resource_proxy.py
Description:
	Proxy resources which result in 403 otherwise
"""

import requests
import json

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import jsonRequest
from utils.encodings import makeUTF8

@app.route('/proxy', methods = ['GET'])
def ajax_resource_proxy():
	if not request.args['url'] or not request.args['header']:
		return ""
	url = makeUTF8(request.args['url'])
	header = makeUTF8(json.loads(request.args['header']))
	ret = requests.get(url, headers = header)
	return ret.content
	
