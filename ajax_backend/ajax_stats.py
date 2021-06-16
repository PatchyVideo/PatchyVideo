
import time

import redis

from flask import render_template, request, current_app, jsonify, redirect, session

from init import app
from utils import getDefaultJSON, getOffsetLimitJSON
from utils.interceptors import basePage, loginOptional, jsonRequest, loginRequiredJSON
from utils.jsontools import *
from utils.exceptions import UserError
from services.tcb import filterOperation

from services.stats import site_stats

from dateutil.parser import parse
from datetime import timezone

@app.route('/stats.do', methods = ['POST', 'GET'])
@basePage
def ajax_stats_do(rd, data):
	users, tags = site_stats()
	return "json", makeResponseSuccess({'users': users, 'top_tags': tags})
