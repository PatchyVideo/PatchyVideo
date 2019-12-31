

from .init import routes, init_funcs

from scraper.video import dispatch

from utils.jsontools import *
from utils.logger import log

@routes.post("/get_ytb_info")
async def get_ytb_info(request):
	url = await request.json()['url']
	log(obj = {'url': url})
	obj, cleanURL = dispatch(url)
	if obj.NAME != 'youtube' :
		log(obj = {'msg': 'NOT_YOUTUBE'})
		return makeResponseFailed('NOT_YOUTUBE')
	info = await obj.get_metadata_async(obj, cleanURL, False)
	if info["status"] != 'SUCCEED' :
		log(obj = {'msg': 'FETCH_FAILED', 'info': info})
		return makeResponseFailed('FETCH_FAILED')
	return info

@routes.post("/get_twitter_info")
def get_twitter_info(request):
	url = await request.json()['url']
	log(obj = {'url': url})
	obj, cleanURL = dispatch(url)
	if obj.NAME != 'twitter' :
		log(obj = {'msg': 'NOT_TWITTER'})
		return makeResponseFailed('NOT_TWITTER')
	info = await obj.get_metadata_async(obj, cleanURL, False)
	if info["status"] != 'SUCCEED' :
		log(obj = {'msg': 'FETCH_FAILED', 'info': info})
		return makeResponseFailed('FETCH_FAILED')
	return info
