
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText
from dateutil.parser import parse
from datetime import timedelta

class Bilibili( Spider ) :
	NAME = 'bilibili'
	PATTERN = r'^(https:\/\/|http:\/\/)?(www\.)?bilibili\.com\/video\/[aA][vV][\d]+'
	SHORT_PATTERN = r'^[aA][Vv][\d]+$'
	HEADERS = makeUTF8( { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }

	def expand_url( self, short ) :
		return "https://www.bilibili.com/video/" + short.lower()

	def unique_id( self, link ) :
		link = link.lower()
		return 'bilibili:%s' % link[link.rfind("av"):]
	
	def run( self, content, xpath, link ) :
		link = link.lower()
		vidid = link[link.rfind("av"):]
		thumbnailURL = xpath.xpath( '//meta[@itemprop="thumbnailUrl"]/@content' )[0]
		title = xpath.xpath( '//h1[@class="video-title"]/@title' )[0]
		desc = getInnerText(xpath.xpath( '//div[@class="info open"]/node()' ))
		uploadDate = parse(xpath.xpath( '//meta[@itemprop="uploadDate"]/@content' )[0]) - timedelta(hours = 8) # convert from Beijing time to UTC
		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'bilibili',
			'uploadDate' : uploadDate,
			"unique_id": "bilibili:%s" % vidid
		})

	async def unique_id_async( self, link ) :
		return self.unique_id(link)
		
	async def run_async(self, content, xpath, link) :
		return self.run(self = self, content = content, xpath = xpath, link = link)
