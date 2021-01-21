
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
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
		'X-Frontend-Id': '6',
		'X-Frontend-Version': '0',
		'X-Niconico-Language': 'ja-jp'
	}
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
		if not url :
			return {
				"desc": "not available",
				"title": "not available"
			}
		website_pid = self.get_pid(self, url)
		api_url = f"https://nvapi.nicovideo.jp/v2/mylists/{website_pid}?pageSize=1&page=1"
		async with aiohttp.ClientSession() as session:
			async with session.get(api_url, headers = self.headers) as resp:
				if resp.status == 200 :
					web_content = await resp.text()
				else :
					web_content = await resp.text()
					log_ne(op = 'nicovideo_mylist_get_metadata', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'url': url, 'resp': web_content.content})
					raise Exception('failed to fetch playlist')
		meta_json = loads(web_content)['data']['mylist']
		if not meta_json["description"] :
			meta_json["description"] = f'Playlist from from {url}\nat {str(datetime.now())}'
		return {
			"desc": meta_json["description"],
			"title": meta_json["name"]
			}

	async def run(self, url = None, website_pid = None) :
		if website_pid and not url :
			url = f"https://nvapi.nicovideo.jp/v2/mylists/{website_pid}?pageSize=1000&page=1"
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers = self.headers) as resp:
				if resp.status == 200 :
					web_content = await resp.text()
				else :
					web_content = await resp.text()
					log_ne(op = 'nicovideo_mylist_run', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'url': url, 'resp': web_content.content})
					raise Exception('failed to fetch playlist')
		data_json = loads(web_content)
		
		for item in data_json['data']['mylist']['items'] :
			yield item['watchId']


