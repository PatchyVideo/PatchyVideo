
import json
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import try_get_xpath
import requests
from urllib.parse import parse_qs
import time
from datetime import datetime
from dateutil.parser import parse
import aiohttp

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
	PATTERN = r'^((https:\/\/)?(www\.|m\.)?youtube\.com\/watch\?v=[-\w]+|https:\/\/youtu\.be\/(watch\?v=[-\w]+|[-\w]+))'
	SHORT_PATTERN = r''
	HEADERS = makeUTF8( { 'Referer' : 'https://www.youtube.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )

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
		return self.unique_id(link)

	def run( self, content, xpath, link ) :
		if 'youtube.com' in link:
			vidid = link[link.rfind('=') + 1:]
		elif 'youtu.be' in link:
			if 'watch?v=' in link:
				vidid = link[link.rfind('=') + 1:]
			else:
				vidid = link[link.rfind('/') + 1:]
		
		thumbnailURL = "https://img.youtube.com/vi/%s/hqdefault.jpg" % vidid

		info_file_link = "https://www.youtube.com/get_video_info?video_id=" + vidid
		info_file = requests.get(info_file_link, headers = self.HEADERS).text
		player_response = parse_qs(info_file)['player_response'][0]
		player_response = json.loads(player_response)
		videoDetails = player_response['videoDetails']
		# everything will end on January 19th 2038

		
		# TODO: this method is incorrect for old videos
		min_timestamp = int(time.time() * 1e6)
		if 'streamingData' in player_response:
			streamingData = player_response['streamingData']
			if 'adaptiveFormats' in streamingData:
				for item in streamingData['adaptiveFormats']:
					try:
						min_timestamp = min(min_timestamp, int(item['lastModified']))
					except:
						pass
			if 'formats' in streamingData:
				for item in streamingData['formats']:
					try:
						min_timestamp = min(min_timestamp, int(item['lastModified']))
					except:
						pass
		min_timestamp *= 1e-6

		uploadDate1 = datetime.fromtimestamp(min_timestamp)
		
		try :
			to_find = '"dateText":{"simpleText":'
			pos_start = content.find(to_find)
			pos_left_quote = content.find('\"', pos_start + len(to_find)) + 1
			pos_right_quote = content.find('\"', pos_left_quote + 1)
			uploadDate_str = content[pos_left_quote:pos_right_quote]
			uploadDate2 = parse(uploadDate_str)

			if abs((uploadDate1 - uploadDate2).total_seconds()) < 3 * 24 * 60 * 60:
				uploadDate = uploadDate1
			else:
				uploadDate = min(uploadDate1, uploadDate2)
		except:
			uploadDate = uploadDate1

		title = videoDetails['title']
		desc = videoDetails['shortDescription']

		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'youtube',
            'uploadDate' : uploadDate,
			"unique_id": "youtube:%s" % vidid
		})
		
	async def run_async( self, content, xpath, link ) :
		if 'youtube.com' in link:
			vidid = link[link.rfind('=') + 1:]
		elif 'youtu.be' in link:
			if 'watch?v=' in link:
				vidid = link[link.rfind('=') + 1:]
			else:
				vidid = link[link.rfind('/') + 1:]
		
		thumbnailURL = "https://img.youtube.com/vi/%s/hqdefault.jpg" % vidid

		info_file_link = "https://www.youtube.com/get_video_info?video_id=" + vidid
		async with aiohttp.ClientSession() as session:
			async with session.post(info_file_link, headers = self.HEADERS) as resp:
				info_file = await resp.text()
		player_response = parse_qs(info_file)['player_response'][0]
		player_response = json.loads(player_response)
		videoDetails = player_response['videoDetails']
		# everything will end on January 19th 2038

		
		# TODO: this method is incorrect for old videos
		min_timestamp = int(time.time() * 1e6)
		if 'streamingData' in player_response:
			streamingData = player_response['streamingData']
			if 'adaptiveFormats' in streamingData:
				for item in streamingData['adaptiveFormats']:
					try:
						min_timestamp = min(min_timestamp, int(item['lastModified']))
					except:
						pass
			if 'formats' in streamingData:
				for item in streamingData['formats']:
					try:
						min_timestamp = min(min_timestamp, int(item['lastModified']))
					except:
						pass
		min_timestamp *= 1e-6

		uploadDate1 = datetime.fromtimestamp(min_timestamp)
		
		try :
			to_find = '"dateText":{"simpleText":'
			pos_start = content.find(to_find)
			pos_left_quote = content.find('\"', pos_start + len(to_find)) + 1
			pos_right_quote = content.find('\"', pos_left_quote + 1)
			uploadDate_str = content[pos_left_quote:pos_right_quote]
			uploadDate2 = parse(uploadDate_str)

			if abs((uploadDate1 - uploadDate2).total_seconds()) < 3 * 24 * 60 * 60:
				uploadDate = uploadDate1
			else:
				uploadDate = min(uploadDate1, uploadDate2)
		except:
			uploadDate = uploadDate1

		title = videoDetails['title']
		desc = videoDetails['shortDescription']

		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'youtube',
            'uploadDate' : uploadDate,
			"unique_id": "youtube:%s" % vidid
		})
