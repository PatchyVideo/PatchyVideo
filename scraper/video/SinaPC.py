from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8

from bs4 import BeautifulSoup
import re
from dateutil.parser import parse
from datetime import timezone

#url = 'https://weibo.com/tv/v/Iv79oyX8i?fid=1034:4474081777483785'

class SinaPC(Crawler):
	NAME = 'weibo-pc'
	SHORT_PATTERN = r''
	PATTERN = r'^(https:\/\/|http:\/\/)?weibo\.(com|cn)\/tv\/v\/(\w+)\?fid=(\d+:\d+)'
	Cookie = 'SINAGLOBAL=4002460776686.9824.1585321155178; UOR=,,m.weibo.cn; YF-V5-G0=125128c5d7f9f51f96971f11468b5a3f; _s_tentry=-; Apache=8703795817895.288.1585556164345; ULV=1585556164370:2:2:1:8703795817895.288.1585556164345:1585321155211; YF-Page-G0=091b90e49b7b3ab2860004fba404a078|1585563210|1585563210; WBStorage=42212210b087ca50|undefined; login_sid_t=52bd5c499b65543341c46965f3d3267b; cross_origin_proto=SSL; Ugrow-G0=7e0e6b57abe2c2f76f677abd9a9ed65d; wb_view_log=2560*14401; WBtopGlobal_register_version=3d5b6de7399dfbdb; crossidccode=CODE-yf-1JiRvU-226WPk-QGmVB9KHtatfm2Ec7ed84; ALF=1617099576; SSOLoginState=1585563577; SUB=_2A25zhbfpDeRhGeBI7lIV9i_IzTuIHXVQ8q4hrDV8PUNbmtANLXDukW9NRpACXBpVshRIjli1oSoWs_HnV-7brere; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhMKKdEqihzDJl7MPTpyF_b5JpX5KzhUgL.FoqcSK5XSo2XSoM2dJLoI7LpUcf.eh.RShqt; SUHB=0WGMeWn5GWqB9T; wvr=6'
	HEADERS = makeUTF8({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0',
						'cookie': Cookie})
	HEADERS_NO_UTF8 = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0',
					   'cookie': Cookie}

	def get_cookie(self) :
		return {
			'SINAGLOBAL' : '4002460776686.9824.1585321155178',
			'UOR' : ',,m.weibo.cn',
			'YF-V5-G0' : '125128c5d7f9f51f96971f11468b5a3f',
			'_s_tentry' : '-',
			'Apache' : '8703795817895.288.1585556164345',
			'ULV' : '1585556164370:2:2:1:8703795817895.288.1585556164345:1585321155211',
			'YF-Page-G0' : '091b90e49b7b3ab2860004fba404a078|1585563210|1585563210',
			'WBStorage' : '42212210b087ca50|undefined',
			'login_sid_t' : '52bd5c499b65543341c46965f3d3267b',
			'cross_origin_proto' : 'SSL',
			'Ugrow-G0' : '7e0e6b57abe2c2f76f677abd9a9ed65d',
			'wb_view_log' : '2560*14401',
			'WBtopGlobal_register_version' : '3d5b6de7399dfbdb',
			'crossidccode' : 'CODE-yf-1JiRvU-226WPk-QGmVB9KHtatfm2Ec7ed84',
			'ALF' : '1617099576',
			'SSOLoginState' : '1585563577',
			'SUB' : '_2A25zhbfpDeRhGeBI7lIV9i_IzTuIHXVQ8q4hrDV8PUNbmtANLXDukW9NRpACXBpVshRIjli1oSoWs_HnV-7brere',
			'SUBP' : '0033WrSXqPxfM725Ws9jqgMF55529P9D9WhMKKdEqihzDJl7MPTpyF_b5JpX5KzhUgL.FoqcSK5XSo2XSoM2dJLoI7LpUcf.eh.RShqt',
			'SUHB' : '0WGMeWn5GWqB9T',
			'wvr' : '6'
		}

	def normalize_url( self, link ) :
		ret = re.search(self.PATTERN, link)
		vid = ret.group(4)
		rnd = ret.group(3)
		return f"https://weibo.com/tv/v/{rnd}?fid={vid}"

	def unique_id(self, link):
		ret = re.search(self.PATTERN, link)
		vid = ret.group(4)
		return f'weibo-pc:{vid}'

	def run(self, content, xpath, link, update_video_detail):
		soup = BeautifulSoup(content, "lxml")
		description = soup.find('div', class_='info_txt W_f14')
		description = description.get_text()
		#user = soup.find('span', class_='W_f14 L_autocut bot_name W_fl')
		#user_name = user.get_text()
		add_time = soup.find('div', class_='broad_time W_f12')
		add_time = add_time.get_text()
		vidid = self.unique_id(self, link)
		return makeResponseSuccess({
			'thumbnailURL': '',
			'title': description,
			'desc': description,
			'site': 'weibo-pc',
			'uploadDate': parse(add_time).astimezone(timezone.utc),
			"unique_id": vidid,
			'utags': []
		})

	async def unique_id_async( self, link ) :
		return self.unique_id(self = self, link = link)

	async def run_async(self, content, xpath, link, update_video_detail):
		return self.run(self=self, content=content, xpath=xpath, link=link, update_video_detail=update_video_detail)
