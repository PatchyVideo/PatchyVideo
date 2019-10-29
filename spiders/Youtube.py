
import json
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
import requests
from urllib.parse import parse_qs

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
	PATTERN = r'^((https:\/\/)?(www\.|m\.)?youtube\.com\/watch\?v=[-\w]+|(https:\/\/)?youtu\.be\/[-\w]+)|(https:\/\/)?youtu\.be\/watch\?v=[-\w]+)'
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
		videoDetails = json.loads(player_response)['videoDetails']

		title = videoDetails['title']
		desc = videoDetails['shortDescription']

		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'youtube',
			"unique_id": "youtube:%s" % vidid
		})
		

