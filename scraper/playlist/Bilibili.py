
import re
import aiohttp
from urllib.parse import urlparse, parse_qs
from bson.json_util import loads
from datetime import datetime

from services.config import Config
from utils.logger import log_ne

class Bilibili() :
	URL_MATCH = re.compile(r'space\.bilibili\.com\/(\d+)\/favlist\?fid=(\d+)')
	EXTRACT_AVID = re.compile(r'(av\d+)')
	def __init__(self) :
		pass

	def test(self, url) :
		ret = self.URL_MATCH.search(url)
		if ret :
			return True
		return False

	def normalize_url(self, url) :
		ret = self.URL_MATCH.search(url)
		uid, fid = ret.groups()
		return f"https://space.bilibili.com/{uid}/favlist?fid={fid}"

	def get_pid(self, url) :
		ret = self.URL_MATCH.search(url)
		uid, fid = ret.groups()
		return fid

	async def get_metadata(self, url = None) :
		ret = self.URL_MATCH.search(url)
		uid, fid = ret.groups()
		page = 1
		api_url = f"https://api.bilibili.com/medialist/gateway/base/spaceDetail?media_id={fid}&pn={page}&ps=1&keyword=&order=mtime&type=0&tid=0&jsonp=jsonp"
		apirespond = None
		async with aiohttp.ClientSession() as session:
			async with session.get(api_url) as resp:
				if resp.status == 200 :
					apirespond = await resp.text()
				else :
					log_ne(op = 'bilibili_playlist_run_async', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'fid': fid, 'uid': uid, 'playlist_url': url, 'resp': apirespond.content, 'url': api_url})
					raise Exception('failed to fetch playlist')
		resp_obj = loads(apirespond)
		return {
			"desc": "Playlist created from " + url + "\nCreated at " + str(datetime.now()),
			"title": resp_obj['data']['info']['title']
			}

	async def run(self, url = None, website_pid = None) :
		if url and not website_pid :
			website_pid = self.get_pid(url)
		async with aiohttp.ClientSession() as session:
			api_url = f"https://api.bilibili.com/medialist/gateway/base/spaceDetail?media_id={website_pid}&pn=1&ps=20&keyword=&order=mtime&type=0&tid=0&jsonp=jsonp"
			async with session.get(api_url) as resp:
				resp_obj = loads(await resp.text())
			media_count = resp_obj['data']['info']['media_count']
			remaining_count = media_count
			for video_obj in resp_obj['data']['medias'] :
				avid = self.EXTRACT_AVID.search(video_obj['short_link']).group(1)
				overrides =  {"desc": video_obj['intro']}
				try :
					overrides["title"] = f"【已失效视频】{video_obj['pages'][0]['title']}"
				except :
					pass
				yield f"https://www.bilibili.com/video/{avid}", overrides
				remaining_count -= 1
			page = 2
			while remaining_count > 0 :
				api_url = f"https://api.bilibili.com/medialist/gateway/base/spaceDetail?media_id={website_pid}&pn={page}&ps=20&keyword=&order=mtime&type=0&tid=0&jsonp=jsonp"
				async with session.get(api_url) as resp:
					resp_obj = loads(await resp.text())
				if len(resp_obj['data']['medias']) == 0 :
					return
				for video_obj in resp_obj['data']['medias'] :
					avid = self.EXTRACT_AVID.search(video_obj['short_link']).group(1)
					overrides =  {"desc": video_obj['intro']}
					try :
						overrides["title"] = f"【已失效视频】{video_obj['pages'][0]['title']}"
					except :
						pass
					yield f"https://www.bilibili.com/video/{avid}", overrides
					remaining_count -= 1
				page += 1


