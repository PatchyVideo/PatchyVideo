
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText

class Bilibili( Spider ) :
    NAME = 'bilibili'
    PATTERN = r'^(https:\/\/|http:\/\/)?(www\.)?bilibili\.com\/video\/av[\d]+'
    SHORT_PATTERN = r'^av[\d]+$'
    HEADERS = makeUTF8( { 'Referer' : 'https://www.bilibili.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )

    def expand_url( self, short ) :
        return "https://www.bilibili.com/video/" + short

    def unique_id( self, link ) :
        return 'bilibili:%s' % link[link.rfind("av"):]

    def run( self, content, xpath, link ) :
        vidid = link[link.rfind("av"):]
        thumbnailURL = xpath.xpath( '//meta[@itemprop="thumbnailUrl"]/@content' )[0]
        title = xpath.xpath( '//h1[@class="video-title"]/@title' )[0]
        desc = getInnerText(xpath.xpath( '//div[@class="info open"]/node()' ))
        return makeResponseSuccess({
            'thumbnailURL': thumbnailURL,
            'title' : title,
            'desc' : desc,
            'site': 'bilibili',
            "unique_id": "bilibili:%s" % vidid
        })
        

