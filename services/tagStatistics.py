
from db import tagdb

import json
import itertools
from collections import Counter

from utils.interceptors import ignoreError
from utils.http import post_json, get_page
from . import TAG_TRACKER_ADDRESS

# TODO: how to update this?
def getPopularTags(max_count = 20) :
    try :
        assert isinstance(max_count, int) and max_count <= 100 and max_count > 0
        response = get_page(TAG_TRACKER_ADDRESS + "/get?count=%d" % max_count)
        json_obj = json.loads(response)
        return json_obj['tags']
    except :
        return []

def getCommonTags(videos, max_count = 20) :
    if len(videos) <= 0 :
        return []
    all_tags = list(itertools.chain(*[vid['tags'] for vid in videos]))
    tag_map = Counter(all_tags).most_common(n = max_count)
    return [item[0] for item in tag_map]

@ignoreError
def updateTagSearch(tags) :
    tags = list(set(tags))
    payload = {
        'hitmap': dict.fromkeys(tags, 1)
    }
    post_json(TAG_TRACKER_ADDRESS + "/hit", payload)
