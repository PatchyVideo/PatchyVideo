
import requests
import json

def post_json(url, json_obj_or_string) :
    if not isinstance(json_obj_or_string, str) :
        payload = json.dumps(json_obj_or_string)
    else :
        payload = json_obj_or_string
    headers = {'content-type': 'application/json'}
    return requests.post(url, data = payload, headers = headers)

def get_page(url) :
    return requests.get(url).text
