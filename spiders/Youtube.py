import json
import sys
import os
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
from utils.logger import log
import requests
from urllib.parse import parse_qs
import time
from datetime import datetime, timezone
from dateutil.parser import parse
import aiohttp
from services.config import Config

def _str(s):
	status = 'normal'
	pos = 0
	while True:
		if s[pos] == '\\' and status == 'normal':
			status = 'trans'
			pos += 1
			continue
		if s[pos] == '"' and status == 'normal':
			break
		status = 'normal'
		pos += 1
	return s[:pos]
		

class Youtube( Spider ) :
	NAME = 'youtube'
	PATTERN = r'^((https:\/\/)?(www\.|m\.)?youtube\.com\/watch\?v=[-\w]+|(https:\/\/)?youtu\.be\/(watch\?v=[-\w]+|[-\w]+))'
	SHORT_PATTERN = r''
	HEADERS = makeUTF8( { 'Referer' : 'https://www.youtube.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.youtube.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }
	API_KEYs = os.getenv('GOOGLE_API_KEYs', "").split(',')
	
	def normalize_url( self, link ) :
		if 'youtube.com' in link:
			vidid = link[link.rfind('=') + 1:]
		elif 'youtu.be' in link:
			if 'watch?v=' in link:
				vidid = link[link.rfind('=') + 1:]
			else:
				vidid = link[link.rfind('/') + 1:]
		return "https://www.youtube.com/watch?v=" + vidid

	def expand_url( self, short ) :
		return short

	def unique_id( self, link ) :
		if 'youtube.com' in link:
			vidid = link[link.rfind('=') + 1:]
		elif 'youtu.be' in link:
			if 'watch?v=' in link:
				vidid = link[link.rfind('=') + 1:]
			else:
				vidid = link[link.rfind('/') + 1:]
		return "youtube:%s" % vidid

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)

	def run( self, content, xpath, link ) :
		if 'youtube.com' in link:
			vidid = link[link.rfind('=') + 1:]
		elif 'youtu.be' in link:
			if 'watch?v=' in link:
				vidid = link[link.rfind('=') + 1:]
			else:
				vidid = link[link.rfind('/') + 1:]

		for key in Config.YOUTUBE_API_KEYS.split(",") :
			api_url = "https://www.googleapis.com/youtube/v3/videos?id=" + vidid + "&key=" + key + "&part=snippet,contentDetails,statistics,status"
			apirespond = requests.get(api_url)# 得到api响应
			if apirespond.status_code == 200 :
				break
			else :
				log(op = 'run', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'key': key, 'resp': apirespond.content, 'url': api_url})

		player_response = apirespond.json()
		player_response = player_response['items'][0]
		player_response = player_response['snippet']
		publishedAt_time = player_response['publishedAt']
		uploadDate = parse(publishedAt_time).astimezone(timezone.utc)#上传时间 格式：2019-04-27 04:58:45+00:00

		title = player_response['title']#标题
		desc = player_response['description']#描述
		thumbnailsurl0 = player_response['thumbnails']
		thumbnailsurl1 = thumbnailsurl0['medium']
		thumbnailURL = thumbnailsurl1['url']#缩略图url size：320 180
		utags = player_response['tags'] if 'tags' in player_response else []

		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'youtube',
            'uploadDate' : uploadDate,
			"unique_id": "youtube:%s" % vidid,
			"utags": utags
		})
		

	async def run_async( self, content, xpath, link ) :
		if 'youtube.com' in link:
			vidid = link[link.rfind('=') + 1:]
		elif 'youtu.be' in link:
			if 'watch?v=' in link:
				vidid = link[link.rfind('=') + 1:]
			else:
				vidid = link[link.rfind('/') + 1:]
		
		for key in Config.YOUTUBE_API_KEYS.split(",") :
			api_url = "https://www.googleapis.com/youtube/v3/videos?id=" + vidid + "&key=" + key + "&part=snippet,contentDetails,statistics,status"
			async with aiohttp.ClientSession() as session:
				async with session.get(api_url, headers = self.HEADERS_NO_UTF8) as resp:
					if resp.status == 200 :
						apirespond = await resp.text()
						break
					else :
						log(op = 'run_async', level = 'WARN', obj = {'msg': 'FETCH_FAILED', 'key': key, 'resp': apirespond.content, 'url': api_url})

		player_response = loads(apirespond)
		player_response = player_response['items'][0]
		player_response = player_response['snippet']
		publishedAt_time = player_response['publishedAt']
		uploadDate = parse(publishedAt_time).astimezone(timezone.utc)

		title = player_response['title']
		desc = player_response['description']
		thumbnailsurl0 = player_response['thumbnails']
		thumbnailsurl1 = thumbnailsurl0['medium']
		thumbnailURL = thumbnailsurl1['url']
		utags = player_response['tags'] if 'tags' in player_response else []

		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'youtube',
            'uploadDate' : uploadDate,
			"unique_id": "youtube:%s" % vidid,
			"utags": utags
		})