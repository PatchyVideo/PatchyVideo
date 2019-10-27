
from . import Spider
from utils.jsontools import *
from utils.encodings import makeUTF8
from utils.html import getInnerText

from services.getVideo import getVideoDetail

class Patchyvideo( Spider ) :
    NAME = 'patchyvideo'
    PATTERN = r'^(https:\/\/|http:\/\/)?(www\.)?(patchyvideo\.com|127\.0\.0\.1:5000|localhost:5000)\/video\?id=\w+'
    SHORT_PATTERN = r''
    LOCAL_SPIDER = True

    def unique_id( self, link ) :
        vidid = link[link.rfind("=") + 1:]
        vidobj = getVideoDetail(vidid)
        if vidobj is None :
            return ''
        return vidobj['item']['unique_id']

    def get_metadata( self, link ) :
        vidid = link[link.rfind("=") + 1:]
        vidobj = getVideoDetail(vidid)
        if vidobj is None :
            return makeResponseFailed({})
        return makeResponseSuccess(vidobj['item'])
        

