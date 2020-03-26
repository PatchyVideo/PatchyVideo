
from flask import render_template, request, current_app, jsonify, redirect, session

from init import app, rdb
from services.logViewer import rankTagContributor
from utils.interceptors import loginOptional, jsonRequest
from utils import getDefaultJSON
from utils.jsontools import *

@app.route('/ranking/tag_contributor.do', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_ranking_tag_contributor_do(rd, data, user):
	hrs = getDefaultJSON(data, 'hrs', 24)
	size = getDefaultJSON(data, 'size', 20)
	return "json", makeResponseSuccess(rankTagContributor(hrs, size))
