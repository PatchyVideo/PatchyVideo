

import time
import urllib

from flask import render_template, request, jsonify, redirect, session

from init import app
from utils.interceptors import loginOptional, loginRequired

from services.user import require_session, logout, query_user

@app.route('/login')
@loginOptional
def pages_login(rd, user) :
    redirect_url = request.referrer or '/'
    if user is not None:
        return "redirect", redirect_url
    else:
        rd.session = require_session("LOGIN")
        rd.redirect_url = urllib.parse.quote(redirect_url)
        return "login.html"

@app.route('/signup')
@loginOptional
def pages_signup(rd, user) :
    if user is not None:
        return "redirect:/"
    else:
        rd.session = require_session("SIGNUP")
        return "signup.html"

@app.route('/logout')
@loginOptional
def pages_logout(rd, user) :
    if user is not None:
        logout(session['sid'])
        del session['sid']
    return "redirect:/"

@app.route("/users/<user_id>", methods=['GET'])
@loginOptional
def pages_userprofile(rd, user, user_id) :
    if user_id == 'me' :
        if user is not None :
            return _render_my_profile(rd, user)
        else :
            return "redirect", "/login"
    else :
        if user is not None :
            if user_id == str(user['_id']) :
                return _render_my_profile(rd, user)
        return _render_user_profile(rd, user, user_id)

def _render_my_profile(rd, user) :
    return "user.html"

def _render_user_profile(rd, user, user_id) :
    obj = query_user(user_id)
    if obj is None :
        return "data", "User does not exist."
    rd.username = obj['profile']['username']
    rd.desc = obj['profile']['desc']
    return "userprofile.html"
