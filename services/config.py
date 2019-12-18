
import os
import redis
rdb = redis.StrictRedis(host = os.getenv('REDISTOGO_URL', 'redis'))

from bson.json_util import dumps

class ConfigCls(object) :
	def __init__(self) :
		pass

	def __getattr__(self, attr) :
		return rdb.get(f'config-{attr}').decode('utf-8')

	def __setattr__(self, attr, value) :
		rdb.set(f'config-{attr}', value)

	def SetValue(self, attr, value) :
		rdb.set(f'config-{attr}', value)

Config = ConfigCls()

def _config(attr, default = '') :
	Config.__setattr__(attr, default)

def _config_env(attr, envvar, default = '') :
	default = os.getenv(envvar, default)
	_config(attr, default)

_config_env("BILICOOKIE_SESSDATA", "bilicookie_SESSDATA")
_config_env("BILICOOKIE_bili_jct", "bilicookie_bili_jct")
_config_env("YOUTUBE_API_KEYS", "GOOGLE_API_KEYs")
