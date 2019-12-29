import sys
import re
from lxml import html
import requests
from utils.jsontools import makeResponseFailed
from utils.http import clear_url
from utils.exceptions import ScraperError
import aiohttp
