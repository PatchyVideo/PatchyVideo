
from db import tagdb

import itertools
from collections import Counter

def getPopularTags(max_count = 20) :
    return []

def getCommonTags(videos, max_count = 20) :
    if len(videos) <= 0 :
        return []
    all_tags = itertools.chain([vid['tags'] for vid in videos])
    tag_map = Counter(all_tags).most_common(n = max_count)
    return [item[0] for item in tag_map]
