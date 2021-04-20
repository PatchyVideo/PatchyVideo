
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText
from urllib.parse import urlparse, parse_qs
from dateutil.parser import parse
from datetime import timedelta, datetime, timezone
from services.config import Config
import aiohttp
import re
import json
import os

from utils.exceptions import UserError

class BilibiliAudio( Crawler ) :
	NAME = 'bilibili_audio'
	PATTERN = r'^(http(s)?:\/\/)?(www\.)?bilibili\.com\/audio\/au(\d+)'
	SHORT_PATTERN = r''
	HEADERS = makeUTF8( { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }

	def normalize_url( self, link ) :
		url_result = re.search(self.PATTERN, link)
		if url_result :
			return f'https://www.bilibili.com/audio/au{url_result.group(4)}'
		else :
			return f'https://www.bilibili.com/audio/au{0}'

	def unique_id( self, link ) :
		url_result = re.search(self.PATTERN, link)
		if url_result :
			return f'bilibili_audio:{url_result.group(4)}'
		else :
			return f''
	
	def run( self, content, xpath, link, update_video_detail ) :
		raise NotImplementedError()

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		url_result = re.search(self.PATTERN, link)
		if url_result :
			auid = url_result.group(4)
		else :
			raise NotImplementedError()
		api_url = f'https://www.bilibili.com/audio/music-service-c/web/song/info?sid={auid}'
		async with aiohttp.ClientSession() as session:
			async with session.get(api_url) as resp :
				api_resp = await resp.json()
		if api_resp['code'] == 0 :
			api_resp = api_resp['data']
			thumbnailURL = api_resp['cover']
			title = api_resp['title']
			desc = api_resp['intro']
			uploadDate = datetime.fromtimestamp(api_resp['passtime']).astimezone(timezone.utc)
			uid = f'bilibili_audio:{auid}'
			utags = []
			user_space_urls = [f'https://space.bilibili.com/{api_resp["uid"]}']
			return makeResponseSuccess({
				'thumbnailURL': thumbnailURL,
				'title' : title,
				'desc' : desc,
				'site': 'bilibili_audio',
				'uploadDate' : uploadDate,
				"unique_id": uid,
				"utags": utags,
				"user_space_urls": user_space_urls,
				'extra': {'vip_info': api_resp['vipInfo']}
			})
		else :
			raise UserError(f'Bilibili API resp code = {api_resp["code"]}')
