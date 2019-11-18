
import requests
import json
from urllib.parse import urlparse

def post_json(url, json_obj_or_string) :
    if not isinstance(json_obj_or_string, str) :
        payload = json.dumps(json_obj_or_string)
    else :
        payload = json_obj_or_string
    headers = {'content-type': 'application/json'}
    return requests.post(url, data = payload, headers = headers)

def post_raw(url, payload) :
    headers = {'content-type': 'text/plain; charset=utf-8'}
    return requests.post(url, data = payload, headers = headers)

def get_page(url) :
    return requests.get(url).text

def clear_url(url) :
    link_parsed = urlparse(url)
    if link_parsed.query :
        return "https://%s%s?%s" % (
            link_parsed.netloc,
            link_parsed.path,
            link_parsed.query)
    else :
        return "https://%s%s" % (
            link_parsed.netloc,
            link_parsed.path)
