
from db import tagdb as db
from db import client
from db.TagDB_language import translateTagToPreferredLanguage
from utils.dbtools import MongoTransaction

import itertools

def _clearOrCreateCollections(session) :
	db.db.utag_tag_freq.delete_many({}, session = session)
	db.db.utag_freq.delete_many({}, session = session)
	db.db.utag_rules.delete_many({}, session = session)

def buildTagRulesFromScratch(utag_threshold = 5, freq_threshold = 3, rule_threshold = 0.8) :
	with MongoTransaction(client) as s :
		_clearOrCreateCollections(s())
		all_tags = db.db.tags.distinct('id', session = s())
		all_utags = db.db.items.distinct('item.utags', session = s())
		ret = db.db.items.aggregate([
			{'$unwind': {'path': '$item.utags'}},
			{'$group': {'_id': '$item.utags', 'count': {'$sum': 1}}}
		], session = s())
		for r in ret :
			db.db.utag_freq.insert_one(r, session = s())
		s.mark_succeed()

	with MongoTransaction(client) as s :
		in_mem_utag_freq = dict([(it['_id'], it['count']) for it in db.db.utag_freq.find({}, session = s())])
		#in_mem_tag_utag_freq = {}
		for (tag, utag) in itertools.product(all_tags, all_utags) :
			if in_mem_utag_freq[utag] < utag_threshold :
				continue
			freq = db.db.items.count_documents({'$and': [{'tags': {'$in': [tag]}}, {'item.utags': {'$in': [utag]}}]}, session = s())
			if freq < freq_threshold :
				continue
			db.db.utag_tag_freq.insert_one({'tag': tag, 'utag': utag, 'freq': freq}, session = s())
			#in_mem_tag_utag_freq[f'{tag} {utag}'] = freq
			prob = float(freq) / float(in_mem_utag_freq[utag])
			if prob > rule_threshold :
				db.db.utag_rules.insert_one({'utag': utag, 'tag': tag}, session = s())
				tag_obj = db.db.tags.find_one({'id': tag}, session = s())
				print('Adding rule {%s} => {%s} with prob = %.2f%%' % (utag, translateTagToPreferredLanguage(tag_obj, 'CHS'), prob * 100))
			else :
				pass
				#print('Ignoring rule {%s} => {%s} with prob = %.2f%%' % (utag, tag, prob * 100))
		s.mark_succeed()

def inferTagidsFromUtags(utags) :
	tags = [it['_id'] for it in db.db.utag_rules.aggregate([{'$match': {'utag': {'$in': utags}}}, {'$group':{'_id': '$tag'}}])]
	return list(set(tags))
