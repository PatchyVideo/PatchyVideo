
from db import tagdb

import json
import itertools
from collections import Counter

from utils.interceptors import ignoreError
from utils.http import post_json, get_page
from utils.tagtools import translateTagsToPreferredLanguage, getTagObjects
from . import TAG_TRACKER_ADDRESS

def getPopularTags(user_language, max_count = 20) :
    try :
        assert isinstance(max_count, int) and max_count <= 100 and max_count > 0
        response = get_page(TAG_TRACKER_ADDRESS + "/get?count=%d" % max_count)
        json_obj = json.loads(response)
        tag_ids = [int(i) for i in json_obj['tags']]
        return tagdb.translate_tag_ids_to_user_language(tag_ids, user_language)[0]
    except :
        return []

def getCommonTags(user_language, videos, max_count = 20) :
    if len(videos) <= 0 :
        return []
    all_tags = list(itertools.chain(*[vid['tags'] for vid in videos]))
    tag_map = Counter(all_tags).most_common(n = max_count)
    tag_ids = [item[0] for item in tag_map]
    return tagdb.translate_tag_ids_to_user_language(tag_ids, user_language)[0]

@ignoreError
def updateTagSearch(tags) :
    tag_ids = tagdb.filter_and_translate_tags(tags)
    payload = {
        'hitmap': dict.fromkeys(tag_ids, 1)
    }
    post_json(TAG_TRACKER_ADDRESS + "/hit", payload)

def getRelatedTagsExperimental(user_language, tags, max_count = 10) :
    tag_ids = tagdb.filter_and_translate_tags(tags)
    related_items = tagdb.db.items.aggregate([
        {'$match': {'tags': {'$in': tag_ids}}},
        {'$project': {'tags': 1}}
    ])
    total_counts = Counter(list(itertools.chain(*[item['tags'] for item in related_items])))
    for tagid in tag_ids :
        del total_counts[tagid]
    total_count = sum(total_counts.values())
    top_tags = total_counts.most_common(n = max_count)
    top_tags_normalized = [(tagid, freq / total_count) for (tagid, freq) in top_tags]
    tagid_to_tag_map = tagdb.translate_tag_ids_to_user_language_map([k for (k, v) in top_tags], user_language)
    top_tags_translated = [{tagid_to_tag_map[tagid]: val} for (tagid, val) in top_tags_normalized]
    return top_tags_translated
