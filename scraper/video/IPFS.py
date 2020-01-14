
import json
import re
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
from dateutil.parser import parse
from datetime import timezone

from datetime import datetime

from lxml.etree import tostring
from bs4 import BeautifulSoup

class IPFS( Crawler ) :
	NAME = 'ipfs'
	PATTERN = r'^https:\/\/ipfs\.globalupload\.io\/[a-zA-Z0-9]+'
	SHORT_PATTERN = r''

	def normalize_url( self, link ) :
		return f"https://ipfs.globalupload.io/" + link[link.rfind("/") + 1:]

	def unique_id( self, link ) :
		return "ipfs:%s" % link[link.rfind("/") + 1:]

	def get_metadata( self, link ) :
		ipfs_hash = link[link.rfind("/") + 1:]
		return makeResponseSuccess({
			'thumbnailURL': '',
			'title' : '【NO TITLE】',
			'desc' : '【NO DESC】',
			'site': 'ipfs',
			'uploadDate' : datetime.now(),
			"unique_id": "ipfs:%s" % ipfs_hash,
			"utags": []
		})
		
	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def get_metadata_async(self, link, update_video_detail = False) :
		return self.get_metadata(self = self, link = link)

