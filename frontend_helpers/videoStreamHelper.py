
from .init import routes, init_funcs

from scraper.video import dispatch

from utils.jsontools import *
from utils.logger import log
from utils.interceptors import asyncJsonRequest

from aiohttp import ClientSession
import os

if os.getenv("FLASK_ENV", "development") == "production" :
   VIDEOSTREAM_ADDRESS = 'http://videostream:5006'
else :
    VIDEOSTREAM_ADDRESS = 'http://localhost:5006'

async def dispatch_presite_extraction(info) :
	return makeResponseSuccess(info)
	# if info['extractor'] == 'BiliBili' :
	# 	ret_info = []
	# 	for quality in info['streams'] :
	# 		ret_info.append({
	# 			'format': quality['container'],
	# 			'quality_desc': quality['quality'],
	# 			'size': quality['size'],
	# 			'src': quality['src']
	# 		})
		
	# else :
	# 	return makeResponseFailed('UNSUPPORTED_WEBSITE')

@routes.post("/get_video_stream")
@asyncJsonRequest
async def get_video_stream_info(request):
	rqjson = (await request.json())
	url = rqjson['url']
	async with ClientSession() as session:
		async with session.post(VIDEOSTREAM_ADDRESS, json={'url': url}) as resp:
			resp_json = await resp.json()
	if 'vs_err' in resp_json :
		return makeResponseFailed({"errinfo": resp_json['vs_err']})
	else :
		return await dispatch_presite_extraction(resp_json)
