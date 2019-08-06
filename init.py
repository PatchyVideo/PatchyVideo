
"""
File:
    main.py
Location:
    /main.py
Description:
    Entry point for PathcyVideo, import all modules from 5 packages: db, pages, ajax_backend, services, utils
    Then run the website
"""

import os

from flask import Flask
from flask_sslify import SSLify
app = Flask('PatchyVideo')
if os.getenv("FLASK_ENV", "development") == "production" :
    sslify = SSLify(app)
app.config.from_object("config.BaseConfig")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '8154d1a2e1e0dad7071a52f05278259a6d97a013315a2e2561689fdfb6f12f4c')

import redis
rdb = redis.StrictRedis(host = os.getenv('REDISTOGO_URL', 'redis'))
