
import re
import aiohttp
import yaml
from urllib.parse import urlparse, parse_qs
from bson.json_util import loads
from datetime import datetime

from services.config import Config
from utils.logger import log_ne

class Nicovideo() :
	URL_MATCH = re.compile(r'mylist\/(\d+)')
	EXTRACT_AVID = re.compile(r'(av\d+)')
	DATA_MATCH_CONTENT = re.compile(r'Mylist\.preload\(\d+,(.+\}\])\);')
	DATA_MATCH_META = re.compile(r'MylistGroup\.preloadSingle\(\d+,[\s]*({.+?})\);', re.S)
	# TODO: known bug: content can not contain });
	def __init__(self) :
		pass

	def test(self, url) :
		ret = self.URL_MATCH.search(url)
		if ret :
			return True
		return False

	def normalize_url(self, url) :
		ret = self.URL_MATCH.search(url)
		mylist_id, = ret.groups()
		return f"https://www.nicovideo.jp/mylist/{mylist_id}"

	def get_pid(self, url) :
		ret = self.URL_MATCH.search(url)
		mylist_id, = ret.groups()
		return mylist_id

	async def get_metadata(self, url = None) :
		async with aiohttp.ClientSession() as session:
			async with session.get(url) as resp:
				if resp.status == 200 :
					web_content = await resp.text()
				else :
					log_ne(op = 'nicovideo_mylist_get_metadata', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'url': url, 'resp': web_content.content})
					raise Exception('failed to fetch playlist')
		ret = self.DATA_MATCH_META.search(web_content)
		meta_json_str, = ret.groups()
		meta_json_str = meta_json_str.replace('\t', ' ')
		meta_json = yaml.safe_load(meta_json_str)
		if not meta_json["description"] :
			meta_json["description"] = f'Playlist from from {url}\nat {str(datetime.now())}'
		return {
			"desc": meta_json["description"],
			"title": meta_json["name"]
			}

	async def run(self, url = None, website_pid = None) :
		if website_pid and not url :
			url = f"https://www.nicovideo.jp/mylist/{website_pid}"
		async with aiohttp.ClientSession() as session:
			async with session.get(url) as resp:
				if resp.status == 200 :
					web_content = await resp.text()
				else :
					log_ne(op = 'nicovideo_mylist_run', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'url': url, 'resp': web_content.content})
					raise Exception('failed to fetch playlist')
		ret = self.DATA_MATCH_CONTENT.search(web_content)
		data_json_str, = ret.groups()
		data_json = loads(data_json_str)
		
		for item in data_json :
			yield item['item_data']['video_id']


