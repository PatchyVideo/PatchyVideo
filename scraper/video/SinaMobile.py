from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import html_to_plain_text

from bs4 import BeautifulSoup
import json
import re
from dateutil.parser import parse
from datetime import timezone

#url = 'https://m.weibo.cn/detail/4473149082711729'

class SinaMobile(Crawler):
	NAME = 'weibo-mobile'
	SHORT_PATTERN = r''
	PATTERN = r'^(https:\/\/|http:\/\/)?m\.weibo\.(com|cn)\/detail\/(\d+)'
	HEADERS = makeUTF8({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0', })
	HEADERS_NO_UTF8 = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0', }

	def normalize_url( self, link ) :
		ret = re.search(self.PATTERN, link)
		vid = ret.group(3)
		return f"https://m.weibo.cn/detail/{vid}"

	def unique_id(self, link):
		ret = re.search(self.PATTERN, link)
		vid = ret.group(3)
		return f'weibo-mobile:{vid}'

	def expand_url(self, num):
		return "https://m.weibo.cn/detail/" + str(num)

	def run(self, content, xpath, link, update_video_detail):#content = page.text
		soup = BeautifulSoup(content, "lxml")
		data = str(soup.select("body  script")[0]).split('var $render_data = [')[1].split('][0]')[0]
		status = json.loads(data)["status"]
		html = json.loads(data)["status"]["text"]
		soup = BeautifulSoup(html, "lxml")
		a_list = soup.findAll('a')
		text = html_to_plain_text(html)
		HYPERLINK = []
		for a in a_list:
			if 'm.weibo.cn/search?' in a.get('href'):
				HYPERLINK.append(a.get('href'))
		for url in HYPERLINK:
			text = text.replace('HYPERLINK', url, 1)
		return makeResponseSuccess({
			"unique_id": self.unique_id(self=self, link=link),
			'uploadDate': parse(status["created_at"]).astimezone(timezone.utc),#Tue Feb 18 02:48:31 +0800 2020
			'thumbnailURL': status["page_info"]["page_pic"]["url"],
			'title': status["page_info"]["title"],
			'site': 'weibo-mobile',
			'desc': text,#超链接
			'utags': []
			})

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)

	async def run_async(self, content, xpath, link, update_video_detail):
		return self.run(self=self, content=content, xpath=xpath, link=link, update_video_detail=update_video_detail)
