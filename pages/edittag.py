
"""
File:
    edittag.py
Location:
    /pages/edittag.py
Description:
    Display edittag page
"""

import time

from flask import render_template, request, jsonify, redirect, session

from main import app
from utils.interceptors import loginOptional, loginRequired

"""
Function:
    pages_edittag
Location:
    /pages/edittag.py
Description:
    display edittag page
"""
@app.route('/edittag')
@loginRequired
def pages_edittag(rd, user):
    return "edittag.html"


