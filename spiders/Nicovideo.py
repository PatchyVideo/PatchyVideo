
import json
import re
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8

from bs4 import BeautifulSoup

class Nicovideo( Spider ) :
    PATTERN = r'^(https:\/\/|http:\/\/)?(www\.)?nicovideo\.jp\/watch\/sm[\d]+'
    SHORT_PATTERN = r'^sm[\d]+$'
    HEADERS = makeUTF8( { 'Referer' : 'https://www.nicovideo.com/', 'User-Agent': '"Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0"' } )

    def expand_url( self, short ) :
        return "https://www.nicovideo.jp/watch/" + short

    def run( self, content, xpath, link ) :
        vidid = link[link.rfind("sm"):]
        try :
            thumbnailURL = xpath.xpath( '//meta[@itemprop="thumbnailUrl"]/@content' )[0]
            title = xpath.xpath( '//meta[@itemprop="name"]/@content' )[0]
            desc = xpath.xpath( '//meta[@itemprop="description"]/@content' )[0]
        except :
            try :
                thumbnailURL = xpath.xpath( '//meta[@name="thumbnail"]/@content' )[0]
                title = xpath.xpath( '//meta[@property="og:title"]/@content' )[0]
                desc = xpath.xpath( '//meta[@name="description"]/@content' )[0]
            except :
                return makeResponseFailed({})
        desc = re.sub(r'<br\s*?>', '\n', desc)
        soup = BeautifulSoup(desc, features = "lxml")
        desc_textonly = ''.join(soup.findAll(text = True))
        return makeResponseSuccess({
            'thumbnailURL': thumbnailURL,
            'title' : title,
            'desc' : desc_textonly,
            'site': 'nicovideo',
            "unique_id": "nicovideo:%s" % vidid
        })
        

