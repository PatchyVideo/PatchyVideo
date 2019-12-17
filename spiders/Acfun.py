
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
from utils.html import getInnerText
from dateutil.parser import parse
from datetime import timedelta, datetime

import re
import os

class Acfun( Spider ) :
	NAME = 'acfun'
	PATTERN = r'^(https:\/\/|http:\/\/)?(www\.)?acfun\.cn\/v\/[aA][cC][\d]+'
	SHORT_PATTERN = r'^[aA][cC][\d]+$'
	HEADERS = makeUTF8( { 'Referer' : 'https://www.acfun.cn/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.acfun.cn/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }
	THUMBNAIL_URL = re.compile(r'https:\/\/imgs\.aixifan\.com\/[\w\-]{8,}')
	THUMBNAIL_URL_2 = re.compile(r'https:\/\/cdn\.aixifan\.com\/dotnet\/[\/\w]+\.(jpg|png)')
	EXTRACT_NUM = re.compile(r'^[\d]+')

	def normalize_url( self, link ) :
		link = link.lower()
		return "https://www.acfun.cn/v/" + link[link.rfind("ac"):]

	def expand_url( self, short ) :
		return "https://www.acfun.cn/v/" + short.lower()

	def unique_id( self, link ) :
		link = link.lower()
		return 'acfun:%s' % link[link.rfind("ac"):]
	
	def run( self, content, xpath, link ) :
		link = link.lower()
		vidid = link[link.rfind("ac"):]
		thumbnailURL = self.THUMBNAIL_URL.search(content)
		if thumbnailURL :
			thumbnailURL = thumbnailURL[0]
		else :
			thumbnailURL = self.THUMBNAIL_URL_2.search(content)
			if thumbnailURL :
				thumbnailURL = thumbnailURL[0]
			else :
				thumbnailURL = ''
		title = xpath.xpath('//h1[@class="title"]/text()')[0]
		desc = try_get_xpath(xpath, ['//div[@class="description-container"]/text()', '//div[@class="J_description"]/text()', '//div[@class="sp1 J_description"]/text()'])[0]
		desc = re.sub(r'<br\s*?\/?>', '\n', desc)
		uploadDate = xpath.xpath('//div[@class="publish-time"]/text()')[0]
		utags = xpath.xpath( '//meta[@name="keywords"]/@content' )[0]
		utags = list(filter(None, utags.split(',')[1: -4]))
		print('utags:', utags)
		try :
			uploadDate = parse(uploadDate) - timedelta(hours = 8)
		except :
			hrs_prior = self.EXTRACT_NUM.match(uploadDate)
			if hrs_prior :
				hrs_prior = int(hrs_prior.group(0))
			else :
				hrs_prior = 0
			uploadDate = datetime.utcnow() - timedelta(hours = hrs_prior)
		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'acfun',
			'uploadDate' : uploadDate,
			"unique_id": "acfun:%s" % vidid,
			"utags": utags
		})

	async def unique_id_async( self, link ) :
		return self.unique_id(link)
		
	async def run_async(self, content, xpath, link) :
		return self.run(self = self, content = content, xpath = xpath, link = link)
