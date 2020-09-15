
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
from utils.html import getInnerText
from dateutil.parser import parse
from datetime import timedelta, datetime

import re
import os

class Zcool( Crawler ) :
	NAME = 'zcool'
	PATTERN = r'^https:\/\/www\.zcool\.com\.cn\/work\/[0-9a-zA-Z=]*\.html'
	SHORT_PATTERN = r''
	HEADERS = makeUTF8( { 'Referer' : 'https://www.zcool.com.cn/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.zcool.com.cn/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }
	DESC_REGEX_OBJ = re.compile(r"share_description\s*=\s*\'(.*)\'\s*;", re.MULTILINE)
	COVER_REGEX_OBJ = re.compile(r'share_description_split,\s*title:\s*\".*\",\s*pic:\s*\"(.*)\"', re.MULTILINE)
	UID_REGEX_OBJ = re.compile(r"^https:\/\/www\.zcool\.com\.cn\/work\/([0-9a-zA-Z=]*)\.html", re.MULTILINE)
	USER_ID_MATCHER = r"(https:\/\/|http:\/\/)?www\.zcool\.com\.cn\/u\/([\d]+)"

	def normalize_url( self, link ) :
		return link

	def expand_url( self, short ) :
		return short

	def unique_id( self, link ) :
		return 'zcool:%s' % self.UID_REGEX_OBJ.search(link).group(1)
	
	def run( self, content, xpath, link, update_video_detail ) :
		if not 'J_prismPlayer0' in content :
			return makeResponseFailed('NOT_ZCOOL_VIDEO')
		zcool_id = self.UID_REGEX_OBJ.search(link).group(1)
		title = xpath.xpath('//span[@class="fw-bold"]/text()')[0]
		
		desc = self.DESC_REGEX_OBJ.search(content).group(1)
		desc = desc.replace('<br>', '\n')

		upload_time = xpath.xpath('//p[@class="title-time"]/@title')[0].split('：')[-1]
		upload_time = parse(upload_time) - timedelta(hours = 8)

		cover = self.COVER_REGEX_OBJ.search(content).group(1)
		cover = cover.split('|')[0].strip().split('@')[0]

		user_id = ''
		user_id_match_result = re.search(self.USER_ID_MATCHER, content)
		if user_id_match_result :
			user_id = user_id_match_result.group(2)
		
		return makeResponseSuccess({
			'thumbnailURL': cover,
			'title' : title,
			'desc' : desc,
			'site': 'zcool',
			'uploadDate' : upload_time,
			"unique_id": "zcool:%s" % zcool_id,
			"user_space_urls": [f"https://www.zcool.com.cn/u/{user_id}"] if user_id else [],
			"utags": []
		})

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		return self.run(self = self, content = content, xpath = xpath, link = link, update_video_detail = update_video_detail)
