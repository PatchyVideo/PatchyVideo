
import aiohttp
from urllib.parse import urlparse, parse_qs
from bson.json_util import loads

from services.config import Config
from utils.logger import log_ne

class Youtube() :
	def __init__(self) :
		pass

	def test(self, url) :
		ret = urlparse(url)
		querys = parse_qs(ret.query)
		if 'youtube.com' in ret.netloc :
			if 'list' in querys :
				return True
		return False

	def normalize_url(self, url) :
		ret = urlparse(url)
		querys = parse_qs(ret.query)
		pid = querys['list'][0]
		return f"https://www.youtube.com/playlist?list={pid}"

	def get_pid(self, url) :
		ret = urlparse(url)
		querys = parse_qs(ret.query)
		pid = querys['list'][0]
		return pid

	async def run(self, url = None, website_pid = None) :
		if url and not website_pid :
			website_pid = self.get_pid(url)
		nextPageToken = ''
		async with aiohttp.ClientSession() as session:
			while True :
				for key in Config.YOUTUBE_API_KEYS.split(",") :
					if nextPageToken :
						api_url = f"https://www.googleapis.com/youtube/v3/playlistItems?pageToken={nextPageToken}&part=snippet&maxResults=50&playlistId={website_pid}&key={key}"
					else :
						api_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={website_pid}&key={key}"
					async with session.get(api_url) as resp:
						if resp.status == 200 :
							apirespond = await resp.text()
							break
						else :
							log_ne(op = 'youtube_playlist_run_async', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'key': key, 'resp': apirespond.content, 'url': api_url})
				ret = loads(apirespond)
				for item in ret['items'] :
					video_id = item['resourceId']['videoId']
					yield f"https://www.youtube.com/watch?v={video_id}"
				if 'nextPageToken' in ret :
					nextPageToken = ret['nextPageToken']
					continue
				else :
					break


