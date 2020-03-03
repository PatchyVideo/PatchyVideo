
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText
from dateutil.parser import parse
from datetime import timedelta, datetime
from services.config import Config
import aiohttp

import os

class Bilibili( Crawler ) :
	NAME = 'bilibili'
	PATTERN = r'^(https:\/\/|http:\/\/)?((www|m)\.)?(bilibili\.com\/video\/[aA][vV][\d]+|b23\.tv\/[aA][vV][\d]+)'
	SHORT_PATTERN = r'^[aA][Vv][\d]+$'
	HEADERS = makeUTF8( { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }

	def get_cookie(self) :
		return {
			'SESSDATA' : Config.BILICOOKIE_SESSDATA,
			'bili_jct' : Config.BILICOOKIE_bili_jct
		}

	def normalize_url( self, link ) :
		link = link.lower()
		return "https://www.bilibili.com/video/" + link[link.rfind("av"):]

	def expand_url( self, short ) :
		return "https://www.bilibili.com/video/" + short.lower()

	def unique_id( self, link ) :
		link = link.lower()
		return 'bilibili:%s' % link[link.rfind("av"):]
	
	def run( self, content, xpath, link, update_video_detail ) :
		raise NotImplementedError()

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		link = link.lower()
		vidid = link[link.rfind("av"):]
		if False :
			# use biliplus, try to get metadata from deleted video
			api_url = f"https://www.biliplus.com/api/view?id={vidid[2:]}"
			async with aiohttp.ClientSession() as session:
				async with session.get(api_url) as resp:
					if resp.status == 200 :
						apirespond = await resp.text()
			respond_json = loads(apirespond)
			if 'code' in respond_json and respond_json['code'] == -404 :
				raise Exception('Video not found in biliplus, it is gone forever 😭')
			thumbnailURL = respond_json['pic']
			title = respond_json['title']
			desc = respond_json['description']
			uploadDate = parse(respond_json['created_at']) - timedelta(hours = 8) # convert from Beijing time to UTC
			utags = respond_json['tag']
			return makeResponseSuccess({
				'thumbnailURL': thumbnailURL,
				'title' : title,
				'desc' : desc,
				'site': 'bilibili',
				'uploadDate' : uploadDate,
				"unique_id": "bilibili:%s" % vidid,
				"utags": utags
			})
		try :
			thumbnailURL = xpath.xpath( '//meta[@itemprop="thumbnailUrl"]/@content' )[0]
			title = xpath.xpath( '//h1[@class="video-title"]/@title' )[0]
			desc = getInnerText(xpath.xpath( '//div[@class="info open"]/node()' ))
			uploadDate = parse(xpath.xpath( '//meta[@itemprop="uploadDate"]/@content' )[0]) - timedelta(hours = 8) # convert from Beijing time to UTC
			utags = xpath.xpath( '//meta[@itemprop="keywords"]/@content' )[0]
			utags = list(filter(None, utags.split(',')[1: -4]))
		except :
			return makeResponseSuccess({
				'thumbnailURL': '',
				'title' : '已失效视频',
				'desc' : '已失效视频',
				'site': 'bilibili',
				'uploadDate' : datetime.now(),
				"unique_id": "bilibili:%s" % vidid,
				"utags": [],
				"placeholder": True
			})
		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'bilibili',
			'uploadDate' : uploadDate,
			"unique_id": "bilibili:%s" % vidid,
			"utags": utags
		})
