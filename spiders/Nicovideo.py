
import json
import re
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
from dateutil.parser import parse
from datetime import timezone

from lxml.etree import tostring
from bs4 import BeautifulSoup

class Nicovideo( Spider ) :
	NAME = 'nicovideo'
	PATTERN = r'^(https:\/\/|http:\/\/)?(www\.)?nicovideo\.jp\/watch\/sm[\d]+'
	SHORT_PATTERN = r'^sm[\d]+$'
	HEADERS = makeUTF8( { 'Referer' : 'https://www.nicovideo.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )

	def expand_url( self, short ) :
		return "https://www.nicovideo.jp/watch/" + short

	def unique_id( self, link ) :
		return "nicovideo:%s" % link[link.rfind("sm"):]

	def run( self, content, xpath, link ) :
		vidid = link[link.rfind("sm"):]
		thumbnailURL = try_get_xpath(xpath, ['//meta[@itemprop="thumbnailUrl"]/@content', '//meta[@name="thumbnail"]/@content'])[0]
		title = try_get_xpath(xpath, ['//meta[@itemprop="name"]/@content', '//meta[@property="og:title"]/@content'])[0]
		desc = try_get_xpath(xpath, [
			('//p[@itemprop="description"]', lambda ret : [tostring(ret[0], encoding='UTF-8').decode()]),
			'//meta[@itemprop="description"]/@content',
			'//meta[@name="description"]/@content'])[0]
		uploadDate = try_get_xpath(xpath, ['//meta[@property="video:release_date"]/@content', '//meta[@name="video:release_date"]/@content'])[0]
		desc = re.sub(r'<br\s*?\/?>', '\n', desc)
		soup = BeautifulSoup(desc, features = "lxml")
		desc_textonly = ''.join(soup.findAll(text = True))
		uploadDate = parse(uploadDate).astimezone(timezone.utc)
		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc_textonly,
			'site': 'nicovideo',
			'uploadDate' : uploadDate,
			"unique_id": "nicovideo:%s" % vidid
		})
		

