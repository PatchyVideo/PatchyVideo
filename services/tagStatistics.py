
from db import tagdb

import json
import itertools
from collections import Counter

from services.config import Config

from utils.exceptions import noexcept
from utils.http import post_json, get_page
from utils.tagtools import translateTagsToPreferredLanguage, getTagObjects
from utils.logger import log
from . import TAG_TRACKER_ADDRESS

def getPopularTags(user_language, max_count = 20) :
	try :
		assert isinstance(max_count, int) and max_count <= 100 and max_count > 0
		response = get_page(TAG_TRACKER_ADDRESS + "/get?count=%d" % max_count)
		json_obj = json.loads(response)
		tag_ids = [int(i) for i in json_obj['tags']]
		tags, _, _ = tagdb.translate_tag_ids_to_user_language(tag_ids, user_language, id_data_map = json_obj['pops'])
		return [i[0] for i in tags], {i[0]: i[1] for i in tags}
	except :
		return [], {}

def getCommonTags(user_language, videos, max_count = 20) :
	if len(videos) <= 0 :
		return []
	all_tags = list(itertools.chain(*[vid['tags'] for vid in videos]))
	tag_map = Counter(all_tags).most_common(n = max_count)
	tag_ids = [item[0] for item in tag_map]
	return tagdb.translate_tag_ids_to_user_language(tag_ids, user_language)[0]

def getCommonTagsWithCount(user_language, videos, max_count = 20) :
	if len(videos) <= 0 :
		return []
	all_tags = list(itertools.chain(*[vid['tags'] for vid in videos]))
	tag_map = Counter(all_tags).most_common(n = max_count)
	tag_ids = [item[0] for item in tag_map]
	return tagdb.translate_tag_ids_to_user_language_with_count(tag_ids, user_language)[0]

@noexcept
def updateTagSearch(tags) :
	tag_ids = tagdb.filter_and_translate_tags(tags)
	default_blacklist_poptag_tagids = [int(i) for i in Config.DEFAULT_BLACKLIST_POPULAR_TAG.split(',')]
	tag_ids = list(set(tag_ids) - set(default_blacklist_poptag_tagids))
	payload = {
		'hitmap': dict.fromkeys(tag_ids, 1)
	}
	post_json(TAG_TRACKER_ADDRESS + "/hit", payload)

def getRelatedTagsExperimental(user_language, tags, exclude = [], max_count = 10) :
	log(obj = {'tags': tags, 'lang': user_language, 'count': max_count})
	tag_ids = tagdb.filter_and_translate_tags(tags)
	exclude_tag_ids = tagdb.filter_and_translate_tags(exclude)
	top_tags = list(tagdb.db.items.aggregate([
		{'$match': {'tags': {'$all': tag_ids}}},
		{'$project': {'tags': 1}},
		{'$unwind': {'path': '$tags'}},
		{'$match': {'tags': {'$lt': 0x80000000}}},
		{'$group': {'_id': '$tags', 'count': {'$sum': 1}}},
		{'$match': {'_id': {'$nin': exclude_tag_ids}}},
		{'$sort': {'count': -1}},
		{'$limit': max_count}
		]))
	total_count = sum(item['count'] for item in top_tags)
	top_tags_normalized = [(item['_id'], item['count'] / total_count) for item in top_tags]
	tagid_to_tag_map = tagdb.translate_tag_ids_to_user_language_map([item['_id'] for item in top_tags], user_language)
	top_tags_translated = [{tagid_to_tag_map[tagid]: val} for (tagid, val) in top_tags_normalized]
	return top_tags_translated

def remove_stop_words(words, stopwords) :
    return [word for word in words if word not in stopwords]

def getRelatedTagsFixedMainTags(user_language, tags, exclude = [], max_count = 10) :
	exclude_tag_ids = tagdb.filter_and_translate_tags(exclude)
	exclude_tags, _, _ = tagdb.translate_tag_ids_to_user_language(exclude_tag_ids, 'CHS')
	all_tags = remove_stop_words(['东方MMD',
		'剧情MMD',
		'舞蹈MMD',
		'东方3D',
		'游戏',
		'东方FTG',
		'东方STG',
		'游戏宣传',
		'音乐游戏',
		'mugen',
		'Minecraft',
		'实况',
		'攻略',
		'跑团',
		'音乐',
		'东方Arrange',
		'东方风Arrange',
		'东方PV',
		'MV',
		'演奏',
		'东方手书',
		'漫画',
		'动画',
		'有配音',
		'Walfas',
		'MAD',
		'AMV',
		'音MAD',
		'鬼畜',
		'东方杂谈',
		'东方科普',
		'东方考据',
		'访谈',
		'电台',
		'排行',
		'线下活动',
		'Cosplay',
		'绘画过程',
		'meme',
		'Shitpost',
		'手工艺',
		'VTuber',
		'图集',
		'主标签完成'], exclude_tags)
	return [{k: 1} for k in all_tags]
