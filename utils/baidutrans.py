
#from https://pypi.org/project/baidu-trans/

import requests
import hashlib
import urllib.parse
import random
import traceback
import json
import time

from utils.exceptions import UserError

APP_ID = '20200814000543070' #你的appid
SECRET_KEY = 'GZWWEwgVh2a0OL7itzA6' #你的密钥

# base api url
BASE_URL = 'api.fanyi.baidu.com'
API_URL = '/api/trans/vip/translate'

LANG_MAP = {
	'zh-CN': 'zh',
	'zh-TW': 'cht',
	'ja': 'jp',
	"en": 'en',
	"ko": 'kor',
	"cs": 'cs',
	#"nl": 'en', # not supported
	"fr": 'fra',
	"de": 'de',
	"hu": 'hu',
	"it": 'it',
	"pl": 'pl',
	"pt": 'pt',
	"ro": 'rom',
	"ru": 'ru',
	"es": 'spa',
	#"tr": 'en', # not supported
	"vi": 'vie'
}

class Translator(object):
	def __init__(self):
	   pass

	def translate(self, from_lang, to_lang, query_text):
		import sys
		if to_lang not in LANG_MAP :
			to_lang = 'en'#raise UserError('UNSUPPORTED_LANGUAGE')
		from_lang = 'jp'
		url = self.get_url(from_lang, LANG_MAP[to_lang], query_text)
		try:
			response = requests.get('https://'+BASE_URL+url).text
			print(response, file = sys.stderr)
			result = json.loads(response)
			result_list = []
			for ret in result["trans_result"]:
				for v in ret["dst"].split('\n') :
					result_list.append(v)
			return result_list
		except Exception as e:
			traceback.print_exc()

	@staticmethod
	def get_url(from_lang, to_lang, query_text):
		# 随机数据
		salt = random.randint(32768, 65536)
		# MD5生成签名
		sign = APP_ID + query_text + str(salt) + SECRET_KEY
		m1 = hashlib.md5()
		m1.update(sign.encode('utf-8'))
		sign = m1.hexdigest()
		# 拼接URL
		url = API_URL +'?appid=' + APP_ID + '&q=' + urllib.parse.quote(query_text) + '&from=' + from_lang + '&to=' + to_lang + '&salt=' + str(salt) + '&sign=' + sign
		return url

