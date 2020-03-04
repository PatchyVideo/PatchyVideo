
from db import tagdb as db
from db import client
from db.TagDB_language import translateTagToPreferredLanguage
from utils.dbtools import MongoTransaction
from utils.logger import log
from collections import defaultdict
from db.index.textseg import cut_for_search

import itertools

def _clearOrCreateCollections(session) :
	db.db.vid_tags.delete_many({}, session = session)
	db.db.utag_tag_freq.delete_many({}, session = session)
	db.db.utag_freq.delete_many({}, session = session)
	db.db.utag_rules.delete_many({}, session = session)

def buildTagRulesFromScratch(vid_tags_threshold = 4, utag_threshold = 5, freq_threshold = 3, rule_threshold = 0.7) :
	with MongoTransaction(client) as s :
		_clearOrCreateCollections(s())
		s.mark_succeed()

	for vid in db.db.items.find({'tags': {'$gte': vid_tags_threshold}}) :
		utags = vid['item']['utags'] if 'utags' in vid['item'] else []
		utags = [u.lower() for u in utags]
		title_utags = cut_for_search(vid['item']['title'])
		desc_utags = cut_for_search(vid['item']['desc'])
		all_utags = list(set(utags + title_utags + desc_utags))
		tag_ids = list(filter(lambda x: x < 0x80000000, vid['tags']))
		db.db.vid_tags.insert_one({'utags': all_utags, 'tags': tag_ids})		

	with MongoTransaction(client) as s :
		ret = db.db.vid_tags.aggregate([
			{'$unwind': {'path': '$utags'}},
			{'$group': {'_id': '$utags', 'count': {'$sum': 1}}}
		], session = s())
		for r in ret :
			db.db.utag_freq.insert_one(r, session = s())
		s.mark_succeed()

	with MongoTransaction(client) as s :
		in_mem_utag_freq = dict([(it['_id'], it['count']) for it in db.db.utag_freq.find({}, session = s())])
		in_mem_tag_utag_freq = defaultdict(int)
		for video_item in db.db.vid_tags.find({}, session = s()) :
			cur_tags = video_item['tags']
			cur_utags = video_item['utags']
			for (tag, utag) in itertools.product(cur_tags, cur_utags) :
				in_mem_tag_utag_freq[(tag, utag)] += 1
		db.db.utag_tag_freq.insert_many([{'tag': tag, 'utag': utag, 'freq': freq} for ((tag, utag), freq) in in_mem_tag_utag_freq.items()], session = s())
		for ((tag, utag), freq) in in_mem_tag_utag_freq.items() :
			if freq < freq_threshold :
				continue
			if in_mem_utag_freq[utag] < utag_threshold :
				continue
			prob = float(freq) / float(in_mem_utag_freq[utag])
			if prob > rule_threshold :
				db.db.utag_rules.insert_one({'utag': utag, 'tag': tag}, session = s())
				tag_obj = db.db.tags.find_one({'id': tag}, session = s())
				print('Adding rule {%s} => {%s} with prob = %.2f%%' % (utag, translateTagToPreferredLanguage(tag_obj, 'CHS'), prob * 100))
		s.mark_succeed()

def inferTagidsFromUtags(utags) :
	tags = [it['_id'] for it in db.db.utag_rules.aggregate([{'$match': {'utag': {'$in': utags}}}, {'$group':{'_id': '$tag'}}])]
	return list(set(tags))

def inferTagsFromUtags(utags, user_language) :
	log(obj = {'utags': utags, 'lang': user_language})
	utags = list(set(utags))
	tagids = inferTagidsFromUtags(utags)
	return db.translate_tag_ids_to_user_language(tagids, user_language)[0]

def inferTagsFromVideo(utags, title, desc, user_language) :
	log(obj = {'title': title, 'desc': desc, 'utags': utags, 'lang': user_language})
	utags = [u.lower() for u in utags]
	title_utags = cut_for_search(title)
	desc_utags = cut_for_search(desc)
	tagids = inferTagidsFromUtags(utags + title_utags + desc_utags)
	return db.translate_tag_ids_to_user_language(tagids, user_language)[0]

