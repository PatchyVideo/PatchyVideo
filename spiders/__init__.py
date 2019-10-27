
import re
from lxml import html
import requests
from utils.jsontools import makeResponseFailed
from utils.http import clear_url

class Spider :
	def __init__(self) :
		pass
	def get_metadata( self, link ) :
		try :
			link = clear_url(link)
			page = requests.get( link, headers = self.HEADERS )
			if page.status_code == 200 :
				tree = html.fromstring( page.text )
				return self.run( self = self, content = page.text, xpath = tree, link = link )
			else :	
				return makeResponseFailed({'status_code': page.status_code})
		except Exception as ex :
			return makeResponseFailed({'exception': str(ex)})
	def get_unique_id( self, link ) :
		link = clear_url(link)
		return self.unique_id( self = self, link = link )

_spider_modules = [ 'Patchyvideo', 'Bilibili', 'Youtube', 'Nicovideo', 'Twitter' ]

_dispatch_map = []

for m in _spider_modules :
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
			return target, match_result.group( 0 )
	return None, None

def dispatch_no_expand( url ) :
	url = url.strip()
	for [ reg, _, target ] in _dispatch_map :
		match_result = re.match( reg, url )
		if match_result :
			return target, match_result.group( 0 )
	return None, None

def test():
	url='https://www.nicovideo.jp/watch/sm114513'
	spider, cleanURL=dispatch(url)
	print(spider.get_metadata(spider,cleanURL))





