
import json
import re
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
from dateutil.parser import parse
from datetime import timezone

from lxml.etree import tostring
from bs4 import BeautifulSoup

class Nicovideo( Crawler ) :
	NAME = 'nicovideo'
	PATTERN = r'^(https:\/\/|http:\/\/)?(www\.|sp\.)?(nicovideo\.jp\/watch\/(s|n)m[\d]+|nico\.ms\/(s|n)m[\d]+)'
	SHORT_PATTERN = r'^(s|n)m[\d]+$'
	HEADERS = makeUTF8( { 'Referer' : 'https://www.nicovideo.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.nicovideo.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }
	THUMBNAIL_PATTERN = r'\"(https:\\\\/\\\\/img\.cdn\.nimg\.jp\\\\/s\\\\/nicovideo\\\\/thumbnails\\\\/\d+\\\\/\d+\.\w+\\\\/\w+\?key=\w+)\"'

	#def get_cookie(self) :
	#	return {
	#		'user_session': 'user_session_69318161_02257179b85d2430deb42ca8763071423671fbf8f531ddcf43185de2e376f686',
	#		'user_session_secure': 'NjkzMTgxNjE6ZXIwOW4yM29YdXUueHFCY2d0Qk5mZHlvOVNROGpjTjV1emRaWFRHZDJqMQ',
	#	}

	def normalize_url( self, link ) :
		link = link.lower()
		return "https://www.nicovideo.jp/watch/" + link[link.rfind("m") - 1:]

	def expand_url( self, short ) :
		return "https://www.nicovideo.jp/watch/" + short

	def unique_id( self, link ) :
		link = link.lower()
		return "nicovideo:%s" % link[link.rfind("m") - 1:]

	def run( self, content, xpath, link, update_video_detail ) :
		link = link.lower()
		vidid = link[link.rfind("m") - 1:]
		thumbnailURL = try_get_xpath(xpath, ['//meta[@itemprop="thumbnailUrl"]/@content', '//meta[@name="thumbnail"]/@content'])
		if thumbnailURL :
			thumbnailURL = thumbnailURL[0]
		else :
			url_result = re.search(self.THUMBNAIL_PATTERN, content)
			if url_result :
				thumbnailURL = url_result.group(1).replace('\\\\/', '/')
				import sys
				print(thumbnailURL, file = sys.stderr)
			else :
				thumbnailURL = ''
		title = try_get_xpath(xpath, ['//meta[@itemprop="name"]/@content', '//meta[@property="og:title"]/@content'])[0]
		jsons = try_get_xpath(xpath, ['//script[@type="application/ld+json"]/text()'])
		desc = None
		for json_str in jsons :
			json_obj = json.loads(json_str)
			if '@type' in json_obj and json_obj['@type'] == 'VideoObject' :
				desc = json_obj['description']
				break
		if desc is None :
			desc = try_get_xpath(xpath, [
				('//p[@itemprop="description"]', lambda ret : [tostring(ret[0], encoding='UTF-8').decode()]),
				'//meta[@itemprop="description"]/@content',
				'//meta[@name="description"]/@content'])[0]
		uploadDate = try_get_xpath(xpath, ['//meta[@property="video:release_date"]/@content', '//meta[@name="video:release_date"]/@content'])[0]
		desc = re.sub(r'<br\s*?\/?>', '\n', desc)
		soup = BeautifulSoup(desc, features = "lxml")
		desc_textonly = ''.join(soup.findAll(text = True))
		uploadDate = parse(uploadDate).astimezone(timezone.utc)
		utags = try_get_xpath(xpath, ['//meta[@property="og:video:tag"]/@content', '//meta[@itemprop="og:video:tag"]/@content', '//meta[@name="og:video:tag"]/@content'])
		if utags :
			utags = [str(ut) for ut in utags]
		else :
			utags = []
		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc_textonly,
			'site': 'nicovideo',
			'uploadDate' : uploadDate,
			"unique_id": "nicovideo:%s" % vidid,
			"utags": utags
		})
		
	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		return self.run(self = self, content = content, xpath = xpath, link = link, update_video_detail = update_video_detail)
