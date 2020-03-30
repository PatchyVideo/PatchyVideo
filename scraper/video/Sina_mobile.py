from . import Crawler
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import html_to_plain_text

from bs4 import BeautifulSoup
import json

#url = 'https://m.weibo.cn/detail/4473149082711729'

class Sina_mobile(Crawler):
    NAME = 'sina_mobile'
    HEADERS = makeUTF8({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0', })
    HEADERS_NO_UTF8 = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0', }
    def normalize_url(self, link):
        return link

    def unique_id(self, link):
        for item in link.split('/'):
            if item.isdigit():
                return item

    def expand_url(self, num):
        return "https://m.weibo.cn/detail/" + str(num)

    def run(self, content, link):#content = page.text
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
            "unique_id": "weibo:%s" % status["id"],
            'uploadDate': status["created_at"],#Tue Feb 18 02:48:31 +0800 2020
            'users': status["user"]["screen_name"],
            'thumbnailURL': status["page_info"]["page_pic"]["url"],
            'title': status["page_info"]["title"],
            #'stream_url_hd': status["page_info"]["media_info"]["stream_url_hd"],
            'desc': text#超链接
            })

    async def run_async(self, content, link):
        return self.run(self=self, content=content, link=link)







