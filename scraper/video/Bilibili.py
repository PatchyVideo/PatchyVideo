
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText
from dateutil.parser import parse
from datetime import timedelta, datetime
from services.config import Config
import aiohttp
import re

import os

"""
From https://www.zhihu.com/question/381784377/answer/1099438784
"""
class _bv2av() :
	table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
	tr = {}
	s = [11, 10, 3, 8, 4, 6]
	xor = 177451812
	add = 8728348608
	def __init__(self) :
		for i in range(58) :
			self.tr[self.table[i]]=i

	def dec(self, x) :
		r = 0
		for i in range(6):
			r += self.tr[x[self.s[i]]] * 58 ** i
		return (r - self.add) ^ self.xor

	def enc(self, x) :
		x = (x ^ self.xor) + self.add
		r = list('BV1  4 1 7  ')
		for i in range(6):
			r[self.s[i]] = self.table[x // 58 ** i % 58]
		return ''.join(r)

class Bilibili( Crawler ) :
	NAME = 'bilibili'
	PATTERN = r'^(https:\/\/|http:\/\/)?((www|m)\.)?(bilibili\.com\/video\/([aA][vV][\d]+|BV[a-zA-Z0-9]+)|b23\.tv\/([aA][vV][\d]+|BV[a-zA-Z0-9]+))'
	SHORT_PATTERN = r'^([aA][Vv][\d]+|BV[a-zA-Z0-9]+)$'
	VID_MATCH_REGEX = r"([aA][Vv][\d]+|BV[a-zA-Z0-9]+)"
	HEADERS = makeUTF8( { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }
	BV2AV = _bv2av()

	def get_cookie(self) :
		return {
			'SESSDATA' : Config.BILICOOKIE_SESSDATA,
			'bili_jct' : Config.BILICOOKIE_bili_jct
		}

	def extract_link(self, link) :
		ret = re.search(self.VID_MATCH_REGEX, link)
		vid = ret.group(1)
		if vid[:2].lower() == 'av' :
			vid = vid.lower()
		if vid[:2].upper() == 'BV' :
			vid = 'BV' + vid[2:]
			vid = 'av' + str(self.BV2AV.dec(vid))
		return vid

	def normalize_url( self, link ) :
		return "https://www.bilibili.com/video/" + self.extract_link(self = self, link = link)

	def expand_url( self, short ) :
		return "https://www.bilibili.com/video/" + short

	def unique_id( self, link ) :
		return 'bilibili:%s' % self.extract_link(self = self, link = link)
	
	def run( self, content, xpath, link, update_video_detail ) :
		raise NotImplementedError()

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		vidid = self.extract_link(self = self, link = link)
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
