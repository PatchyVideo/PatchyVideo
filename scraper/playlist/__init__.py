import sys
import re
from lxml import html
import requests
from utils.jsontools import makeResponseFailed
from utils.http import clear_url
from utils.exceptions import ScraperError
import aiohttp

_crawler_modules = [ 'Youtube', 'Bilibili' ]

_dispatch_map = []

for m in _crawler_modules :
	exec( 'from .%s import %s' % (m, m) )
	exec( 'global _dispatch_map; _dispatch_map.append(%s)' % m )

def dispatch( url ) :
	url = clear_url(url.strip())
	for cralwer in _dispatch_map :
		if cralwer.test(self = cralwer, url = url) :
			return cralwer, cralwer.normalize_url(self = cralwer, url = url)
	return None, None
