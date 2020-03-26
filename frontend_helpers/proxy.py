
import json

from .init import routes, init_funcs

from scraper.video import dispatch

from utils.jsontools import *
from utils.logger import log, beginEvent

import aiohttp
from aiohttp import web
from urllib.parse import urlparse, parse_qs

@routes.get("/proxy")
async def fe_proxy(request):
	beginEvent('fe_proxy', request.remote, request.raw_path, None)
	query_dict = parse_qs(urlparse(request.raw_path).query)
	url = query_dict['url'][0] if 'url' in query_dict else ''
	header = query_dict['header'][0] if 'header' in query_dict else ''
	print(url)
	print(header)
	if not url or not header:
		return web.Response(text = "")
	header = json.loads(header)
	async with aiohttp.ClientSession() as session:
		async with session.get(url, headers = header) as resp:
			content = await resp.read()
	log(obj = {'content_length': len(content), 'status_code': resp.status})
	return web.Response(body = content)
