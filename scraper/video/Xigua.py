
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
from utils.html import getInnerText
from dateutil.parser import parse
from datetime import timedelta, datetime, timezone

import re
import os

class Xigua( Crawler ) :
	NAME = 'Xigua'
	PATTERN = r'^https?\:\/\/(www\.)?ixigua.com/(\d+)'
	SHORT_PATTERN = r''
	HEADERS = makeUTF8( { 'Referer' : 'https://www.ixigua.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.ixigua.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }
	META_MATCH_OBJ = r"<script\s+data-react-helmet=\"true\"\s+type=\"application/ld\+json\">\s*(.*?)\s*</script>"
	USER_ID_MATCH_OBJ = r"\"user_id\":(\d+)"

	def get_cookie(self) :
		return {'ttwid': '1%7Cfjd63xV6vk-PylvXbSpJ6X3A6TA9GDxriyUbQWjDsBs%7C1614899329%7C131ef1e44612efea0743459a6fe967e70a2ca5ece23fda9c9b3983354d3d00fe'}

	def normalize_url( self, link ) :
		ret = re.search(self.PATTERN, link)
		vid = ret.group(2)
		return f'https://www.ixigua.com/{vid}'

	def expand_url( self, short ) :
		return short

	def unique_id( self, link ) :
		ret = re.search(self.PATTERN, link)
		vid = ret.group(2)
		return f'xigua:{vid}'
	
	def run( self, content, xpath, link, update_video_detail ) :	
		metadata = re.search(self.META_MATCH_OBJ, content)
		user_id = re.search(self.USER_ID_MATCH_OBJ, content)
		if user_id :
			user_id = user_id.group(1)
		if metadata :
			metadata = loads(metadata.group(1))
			title = metadata['name'].removesuffix(' - 西瓜视频')
			desc = metadata['description']
			cover = metadata['thumbnailUrl'][0] if 'thumbnailUrl' in metadata else metadata['image'][0]
			upload_time = parse(metadata['datePublished']).astimezone(timezone.utc)
		else :
			raise Exception('Cannot find metadata or user_id object')

		return makeResponseSuccess({
			'thumbnailURL': cover,
			'title' : title,
			'desc' : desc,
			'site': 'xigua',
			'uploadDate' : upload_time,
			"unique_id": self.unique_id(self = self, link = link),
			"user_space_urls": [f"https://www.ixigua.com/home/{user_id}"] if user_id else [],
			"utags": []
		})

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		return self.run(self = self, content = content, xpath = xpath, link = link, update_video_detail = update_video_detail)
