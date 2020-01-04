
import os
import redis
rdb = redis.StrictRedis(host = os.getenv('REDISTOGO_URL', 'redis'))

from bson.json_util import dumps
from utils.logger import log

class ConfigCls(object) :
	def __init__(self) :
		pass

	def __getattr__(self, attr) :
		old_val = rdb.get(f'config-{attr}')
		if old_val :
			return old_val.decode('utf-8')
		else :
			return None

	def __setattr__(self, attr, value) :
		self.SetValue(attr, value)

	def ListAttrs(self) :
		ret = {}
		for k in self.__dict__.keys() :
			ret[k] = self.__getattr__(k)
		return ret

	def SetValue(self, attr, value) :
		old_val = self.__getattr__(attr)
		rdb.set(f'config-{attr}', value)
		#log(obj = {'old_val': old_val, 'new_val': value})

Config = ConfigCls()

def _config(attr, default = '') :
	setattr(Config, attr, default)

def _config_env(attr, envvar, default = '') :
	default = os.getenv(envvar, default)
	_config(attr, default)

_config_env("BILICOOKIE_SESSDATA", "bilicookie_SESSDATA")
_config_env("BILICOOKIE_bili_jct", "bilicookie_bili_jct")
_config_env("YOUTUBE_API_KEYS", "GOOGLE_API_KEYs")
