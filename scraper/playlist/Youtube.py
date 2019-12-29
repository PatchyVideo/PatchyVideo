
import aiohttp
from urllib.parse import urlparse, parse_qs
from services.config import Config

class Youtube() :
    def __init__(self) :
        pass

    def test(self, url) :
        ret = urlparse(url)
        querys = parse_qs(ret.query)
        if 'youtube.com' in ret.netloc :
            if 'list' in querys :
                return True
        return False

    def normalize_url(self, url) :
        ret = urlparse(url)
        querys = parse_qs(ret.query)
        pid = querys['list'][0]
        return f"https://www.youtube.com/playlist?list={pid}"

    def unique_id(self, url) :
        ret = urlparse(url)
        querys = parse_qs(ret.query)
        pid = querys['list'][0]
        return f"youtube-list:{pid}"

    async def run(self, url) :
        pass

