
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText

from services.getVideo import getVideoDetailNoFilter

class Patchyvideo( Crawler ) :
	NAME = 'patchyvideo'
	PATTERN = r'^(https:\/\/|http:\/\/)?(www\.)?(patchyvideo\.com|127\.0\.0\.1:5000|localhost:5000)\/video\?id=\w+'
	SHORT_PATTERN = r''
	LOCAL_CRAWLER = True

	def normalize_url( self, link ) :
		return link

	def get_unique_id( self, link ) :
		vidid = link[link.rfind("=") + 1:]
		vidobj = getVideoDetailNoFilter(vidid)
		if vidobj is None :
			return ''
		return vidobj['item']['unique_id']

	def get_metadata( self, link ) :
		vidid = link[link.rfind("=") + 1:]
		vidobj = getVideoDetailNoFilter(vidid)
		if vidobj is None :
			return makeResponseFailed({})
		return makeResponseSuccess(vidobj['item'])
		
	async def get_metadata_async( self, link, update_video_detail = False ) :
		import asyncio
		await asyncio.sleep(30)
		vidid = link[link.rfind("=") + 1:]
		vidobj = getVideoDetailNoFilter(vidid)
		if vidobj is None :
			return makeResponseFailed({})
		return makeResponseSuccess(vidobj['item'])

	async def get_unique_id_async( self, link ) :
		return self.unique_id(link)
		

