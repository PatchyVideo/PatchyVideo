
from functools import partial
import sys
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText
from .impl.twitter_video_download import match1, r1, get_content, post_content
from .yt_dlp.extractor.twitter import TwitterIE
from .yt_dlp.YoutubeDL import YoutubeDL
from .yt_dlp.utils import ExtractorError
from dateutil.parser import parse
from datetime import timezone

import re
import json
import aiohttp
import asyncio

async def adownload_with_yt_dlp(tid: str, tIE) :
	loop = asyncio.get_event_loop()
	pfunc = partial(tIE.extract, f'https://twitter.com/i/status/{tid}')
	return await loop.run_in_executor(None, pfunc)

def download_with_yt_dlp(tid: str, tIE: TwitterIE) :
	return tIE.extract(f'https://twitter.com/i/status/{tid}')

class Twitter( Crawler ) :
	NAME = 'twitter'
	PATTERN = r'^(https:\/\/)?(www\.|mobile\.)?twitter\.com\/[\w]+\/status\/[\d]+'
	SHORT_PATTERN = r''
	HEADERS = makeUTF8({
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',  # noqa
		'Accept-Charset': 'UTF-8,*;q=0.5',
		'Accept-Encoding': 'gzip,deflate,sdch',
		'Accept-Language': 'en-US,en;q=0.8',
		'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0',  # noqa
	})
	HEADERS_NO_UTF8 = {
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',  # noqa
		'Accept-Charset': 'UTF-8,*;q=0.5',
		'Accept-Encoding': 'gzip,deflate,sdch',
		'Accept-Language': 'en-US,en;q=0.8',
		'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0',  # noqa
	}

	def normalize_url( self, link ) :
		if re.match(r'https?://mobile', link): # normalize mobile URL
			link = 'https://' + match1(link, r'//mobile\.(.+)')
		item_id = r1(r'twitter\.com/[^/]+/status/(\d+)', link)
		return "https://twitter.com/i/status/" + item_id

	def unique_id( self, link ) :
		if re.match(r'https?://mobile', link): # normalize mobile URL
			link = 'https://' + match1(link, r'//mobile\.(.+)')
		item_id = r1(r'twitter\.com/[^/]+/status/(\d+)', link)
		return "twitter:%s" % item_id

	def run( self, content, xpath, link ) :
		if re.match(r'https?://mobile', link): # normalize mobile URL
			link = 'https://' + match1(link, r'//mobile\.(.+)')
		screen_name = r1(r'twitter\.com/([^/]+)', link) or r1(r'data-screen-name="([^"]*)"', content) or \
			r1(r'<meta name="twitter:title" content="([^"]*)"', content)
		item_id = r1(r'twitter\.com/[^/]+/status/(\d+)', link) or r1(r'data-item-id="([^"]*)"', content) or \
			r1(r'<meta name="twitter:site:id" content="([^"]*)"', content)
		
		
		dl = YoutubeDL()
		t = TwitterIE(dl)

		info = download_with_yt_dlp(item_id, t)
		if 'extended_entities' not in info :
			return makeResponseFailed('Not a twitter video')
		desc = info['full_text']
		cover = info['entities']['media'][0]['media_url_https']
		user_name = info['user']['name']
		screen_name = info['user']['screen_name']
		uploadDate = parse(info['created_at']).astimezone(timezone.utc)

		return makeResponseSuccess({
			'thumbnailURL': cover,
			'title' : '%s @%s' % (user_name, screen_name),
			'desc' : desc,
			'site': 'twitter',
			'uploadDate' : uploadDate,
			"unique_id": "twitter:%s" % item_id,
			"url_overwrite": f'https://twitter.com/{screen_name}/status/{item_id}',
			"user_space_urls": [f'https://twitter.com/{screen_name}'],
			"utags": []
		})
		
	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		if re.match(r'https?://mobile', link): # normalize mobile URL
			link = 'https://' + match1(link, r'//mobile\.(.+)')
		screen_name = r1(r'twitter\.com/([^/]+)', link) or r1(r'data-screen-name="([^"]*)"', content) or \
			r1(r'<meta name="twitter:title" content="([^"]*)"', content)
		item_id = r1(r'twitter\.com/[^/]+/status/(\d+)', link) or r1(r'data-item-id="([^"]*)"', content) or \
			r1(r'<meta name="twitter:site:id" content="([^"]*)"', content)
		

		dl = YoutubeDL()
		t = TwitterIE(dl)

		info = await adownload_with_yt_dlp(item_id, t)
		if 'extended_entities' not in info :
			return makeResponseFailed('Not a twitter video')
		desc = info['full_text']
		cover = info['entities']['media'][0]['media_url_https']
		user_name = info['user']['name']
		screen_name = info['user']['screen_name']
		uploadDate = parse(info['created_at']).astimezone(timezone.utc)

		return makeResponseSuccess({
			'thumbnailURL': cover,
			'title' : f'{user_name} @{screen_name}',
			'desc' : desc,
			'site': 'twitter',
			'uploadDate' : uploadDate,
			"unique_id": "twitter:%s" % item_id,
			"url_overwrite": f'https://twitter.com/{screen_name}/status/{item_id}',
			"user_space_urls": [f'https://twitter.com/{screen_name}'],
			"utags": []
		})
