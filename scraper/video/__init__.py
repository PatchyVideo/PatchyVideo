import sys
import re
from lxml import html
import requests
from utils.jsontools import makeResponseFailed
from utils.http import clear_url
from utils.exceptions import ScraperError
import aiohttp

class Crawler :
	def __init__(self) :
		pass
	def get_metadata( self, link ) :
		try :
			link = clear_url(link)
			cookie = self.get_cookie(self = self) if hasattr(self, 'get_cookie') else None
			page = requests.get( link, headers = self.HEADERS, cookies = cookie )
			if page.status_code == 200 :
				tree = html.fromstring( page.text )
				return self.run( self = self, content = page.text, xpath = tree, link = link, update_video_detail = False )
			else :	
				return makeResponseFailed({'status_code': page.status_code})
		except Exception as ex :
			return makeResponseFailed({'exception': str(ex)})
	def get_unique_id( self, link ) :
		link = clear_url(link)
		return self.unique_id( self = self, link = link )

	async def get_metadata_async( self, link, update_video_detail = False ) :
		try :
			link = clear_url(link)
			async with aiohttp.ClientSession() as session:
				cookie = self.get_cookie(self = self) if hasattr(self, 'get_cookie') else None
				async with session.get(link, headers = self.HEADERS_NO_UTF8, cookies = cookie) as resp:
					if resp.status == 200 :
						page_content = await resp.text()
						tree = html.fromstring(page_content)
						return await self.run_async( self = self, content = page_content, xpath = tree, link = link, update_video_detail = update_video_detail )
					else :	
						return makeResponseFailed({'status_code': resp.status})
		except Exception as ex :
			import traceback
			print(traceback.format_exc(), file = sys.stderr)
			return makeResponseFailed({'exception': str(ex)})

	async def get_unique_id_async( self, link ) :
		link = clear_url(link)
		return await self.unique_id_async( self = self, link = link )

#_crawler_modules = [ 'Patchyvideo', 'Bilibili', 'Youtube', 'Nicovideo', 'Twitter', 'Acfun', 'IPFS' ]
_crawler_modules = [ 'Bilibili', 'Youtube', 'Nicovideo', 'Twitter', 'Acfun', 'IPFS', 'Zcool', 'SinaMobile', 'Xigua' ]

_dispatch_map = []

for m in _crawler_modules :
	exec( 'from .%s import %s' % (m,m) )
	re_exp = eval( 're.compile( %s.PATTERN, re.IGNORECASE )' % m )
	if eval( '%s.SHORT_PATTERN' % m ) :
		re_exp_short = eval( 're.compile( %s.SHORT_PATTERN, re.IGNORECASE )' % m )
	else :
		re_exp_short = None
	exec( 'global _dispatch_map; _dispatch_map.append( [ re_exp, re_exp_short, %s ] )' % m )

def dispatch( url ) :
	url = url.strip()
	for [ reg, short_exp, target ] in _dispatch_map :
		if short_exp :
			match_result_short = re.match( short_exp, url )
			if match_result_short :
				return target, target.expand_url( target, match_result_short.group( 0 ) )
		match_result = re.match( reg, url )
		if match_result :
			g0 = match_result.group( 0 )
			return target, target.normalize_url( target, g0 )
	return None, None
