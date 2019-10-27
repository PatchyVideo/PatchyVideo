
import os

from flask import Flask
from flask_sslify import SSLify
app = Flask('PatchyVideo')
if os.getenv("FLASK_ENV", "development") == "production" :
    sslify = SSLify(app)
app.config.from_object("config.BaseConfig")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '8154d1a2e1e0dad7071a52f05278259a6d97a013315a2e2561689fdfb6f12f4c')

#from flask_restplus import Resource, Api
#api = Api(app)

import redis
rdb = redis.StrictRedis(host = os.getenv('REDISTOGO_URL', 'redis'))

"""
from flask_swagger_ui import get_swaggerui_blueprint
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Seans-Python-Flask-REST-Boilerplate"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)
"""


import logging
if os.getenv("FLASK_ENV", "development") == "production" :
    logging.basicConfig(filename = '/logs/webapp.log',
                        filemode = 'a',
                        level = 'INFO',
                        format = '%(asctime)-15s %(message)s')
else :
    logging.basicConfig(filename = 'webapp.log',
                        filemode = 'a',
                        level = 'INFO',
                        format = '%(asctime)-15s %(message)s')
logger = logging.getLogger('logger')

