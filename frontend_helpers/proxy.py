
import json

from .init import routes, init_funcs

from scraper.video import dispatch

from utils.jsontools import *
from utils.logger import log, beginEvent

import aiohttp
from aiohttp import web
from urllib.parse import urlparse, parse_qs

import sys

@routes.get("/proxy")
async def fe_proxy(request):
	beginEvent('fe_proxy', request.remote, request.raw_path, None)
	try :
		query_dict = parse_qs(urlparse(request.raw_path).query)
		url = query_dict['url'][0] if 'url' in query_dict else ''
		if not url.startswith('http') and url.startswith('//') :
			url = 'https:' + url
		header = query_dict['header'][0] if 'header' in query_dict else ''
		print('---------URL---------', url, file = sys.stderr)
		# print(header, file = sys.stderr)
		if not url or not header:
			return web.Response(text = "")
		header = json.loads(header)
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers = header) as resp:
				content = await resp.read()
		log(obj = {'content_length': len(content), 'status_code': resp.status})
		return web.Response(body = content)
	except Exception as ex :
		import traceback
		traceback.print_exc()
		return web.Response(body = '')
