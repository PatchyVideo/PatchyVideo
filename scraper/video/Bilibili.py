
from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText
from urllib.parse import urlparse, parse_qs
from dateutil.parser import parse
from datetime import timedelta, datetime
from services.config import Config
import aiohttp
import re
import json
import os

from utils.exceptions import UserError

"""
From https://www.zhihu.com/question/381784377/answer/1099438784
"""
class _bv2av() :
	table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
	tr = {}
	s = [11, 10, 3, 8, 4, 6]
	xor = 177451812
	add = 8728348608
	def __init__(self) :
		for i in range(58) :
			self.tr[self.table[i]]=i

	def dec(self, x) :
		r = 0
		for i in range(6):
			r += self.tr[x[self.s[i]]] * 58 ** i
		return (r - self.add) ^ self.xor

	def enc(self, x) :
		x = (x ^ self.xor) + self.add
		r = list('BV1  4 1 7  ')
		for i in range(6):
			r[self.s[i]] = self.table[x // 58 ** i % 58]
		return ''.join(r)

class Bilibili( Crawler ) :
	NAME = 'bilibili'
	PATTERN = r'^((https:\/\/|http:\/\/)?((www|m)\.)?(bilibili\.com\/video\/([aA][vV][\d]+|BV[a-zA-Z0-9]+)).*|https:\/\/b23\.tv\/\w+)'
	SHORT_PATTERN = r'^([aA][Vv][\d]+|[Bb][Vv][a-zA-Z0-9]+)$'
	VID_MATCH_REGEX = r"([aA][Vv][\d]+|[Bb][Vv][a-zA-Z0-9]+)"
	AID_MATCH_REGEX = r"__INITIAL_STATE__\s*=\s*{\"aid\"\:(\d+),"
	USER_ID_MATCHER = r"\"owner\":{\"mid\":([\d]+)"
	MULTISTAFF_MATCHER = r"\"staff\":(\[{.*?}\])"
	HEADERS = makeUTF8( { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )
	HEADERS_NO_UTF8 = { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' }
	BV2AV = _bv2av()

	def get_cookie(self) :
		return {
			'SESSDATA' : Config.BILICOOKIE_SESSDATA,
			'bili_jct' : Config.BILICOOKIE_bili_jct
		}

	# TODO: can not handle if p number exceeds actual p number of the given video
	def extract_link(self, link) :
		ret = re.search(self.VID_MATCH_REGEX, link)
		if ret is None and 'b23.tv' in link :
			return None, None, True
		parsed_link = urlparse(link)
		qs_dict = parse_qs(parsed_link.query)
		p_num = 1
		try :
			p_num = int(qs_dict['p'][0])
		except :
			pass
		vid = ret.group(1)
		if vid[:2].lower() == 'av' :
			vid = vid.lower()
		if vid[:2].upper() == 'BV' :
			vid = 'BV' + vid[2:]
			vid = 'av' + str(self.BV2AV.dec(vid))
		return vid, p_num, False

	def normalize_url( self, link ) :
		vidid, p_num, b23vid = self.extract_link(self = self, link = link)
		if b23vid :
			return link
		else :
			return f"https://www.bilibili.com/video/{vidid}?p={p_num}"

	def expand_url( self, short ) :
		if short[:2].lower() == 'av' :
			short = short.lower()
		if short[:2].upper() == 'BV' :
			short = 'BV' + short[2:]
			short = 'av' + str(self.BV2AV.dec(short))
		return f"https://www.bilibili.com/video/{short}?p=1"

	def unique_id( self, link ) :
		vidid, p_num, b23vid = self.extract_link(self = self, link = link)
		if b23vid :
			return ''
		else :
			return 'bilibili:%s-%d' % (vidid, p_num)
	
	def run( self, content, xpath, link, update_video_detail ) :
		raise NotImplementedError()

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)
		
	async def run_async(self, content, xpath, link, update_video_detail) :
		uid = ''
		new_url = ''
		try :
			aid, p_num, b23vid = self.extract_link(self = self, link = link)
			if b23vid :
				aid_match = re.search(self.AID_MATCH_REGEX, content)
				aid = 'av' + aid_match.group(1)
				new_url = f"https://www.bilibili.com/video/{aid}?p=1"
				p_num = 1
				uid = 'bilibili:%s-1' % aid
			else :
				new_url = link
				uid = self.unique_id(self = self, link = link)
			aid = aid[2:] # remove 'av'
			thumbnailURL = xpath.xpath( '//meta[@itemprop="thumbnailUrl"]/@content' )[0]
			title = xpath.xpath( '//h1[@class="video-title"]/@title' )[0]
			desc = getInnerText(xpath.xpath( '//div[@class="info open"]/node()' ))
			uploadDate = parse(xpath.xpath( '//meta[@itemprop="uploadDate"]/@content' )[0]) - timedelta(hours = 8) # convert from Beijing time to UTC
			utags = xpath.xpath( '//meta[@itemprop="keywords"]/@content' )[0]
			utags = list(filter(None, utags.split(',')[1: -4]))
			part_name = title
			user_space_urls = []
			multistaff_match_result = re.search(self.MULTISTAFF_MATCHER, content)
			if multistaff_match_result :
				staff_json = json.loads(multistaff_match_result.group(1))
				user_space_urls = ['https://space.bilibili.com/%d' % x['mid'] for x in staff_json]
			else :
				user_space_match_result = re.search(self.USER_ID_MATCHER, content)
				if user_space_match_result :
					user_space_urls = ['https://space.bilibili.com/%s' % user_space_match_result.group(1)]
			cid = 0
			async with aiohttp.ClientSession() as session:
				async with session.get(f'https://api.bilibili.com/x/player/pagelist?aid={aid}&jsonp=jsonp') as resp:
					api_content = await resp.text()
					if resp.status == 200 :
						api_obj = loads(api_content)
						num_parts = len(api_obj['data'])
						if p_num < 1 or p_num > num_parts :
							raise UserError(f'P number out of range, should be in [1, {num_parts}]')
						part_name = api_obj['data'][p_num - 1]['part']
						cid = api_obj['data'][p_num - 1]['cid']
					else :
						raise Exception(f'api request failed, message:\n{api_content}')
		except UserError as ex :
			raise ex
		except :
			return makeResponseSuccess({
				'thumbnailURL': '',
				'title' : '已失效视频',
				'desc' : '已失效视频',
				'site': 'bilibili',
				'uploadDate' : datetime.now(),
				"unique_id": uid,
				"utags": [],
				"url_overwrite": new_url,
				"placeholder": True
			})
		return makeResponseSuccess({
			'thumbnailURL': thumbnailURL,
			'title' : title,
			'desc' : desc,
			'site': 'bilibili',
			'uploadDate' : uploadDate,
			"unique_id": uid,
			"utags": utags,
			"url_overwrite": new_url,
			"user_space_urls": user_space_urls,
			'extra': {'part_name': part_name, 'cid': cid}
		})
