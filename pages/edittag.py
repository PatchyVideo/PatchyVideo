
import time

from flask import render_template, request, jsonify, redirect, session

from main import app
from utils.interceptors import loginOptional, loginRequired

@app.route('/edittag')
@loginRequired
def pages_edittag(rd, user):
    return "edittag.html"


