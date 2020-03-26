

import redis_lock

from .textseg import cut_for_index

from init import rdb
from db import client, db
from utils.dbtools import MongoTransaction

def remove_index(word_ids, session = None) :
	word_ids = [int(i) & 0x7FFFFFFF for i in word_ids]
	db.index_words.update_many({'_id': {'$in': word_ids}}, {'$inc': {'freq': int(-1)}}, session = session)

def build_index(txt, session = None) :
	if not txt :
		return []
	words = cut_for_index(txt)
	with redis_lock.Lock(rdb, "building_index") :
		found_word_objs = list(db.index_words.find({'word': {'$in': words}}, session = session))
		words_map = {w: False for w in words}
		for found_word_obj in found_word_objs :
			words_map[found_word_obj['word']] = True
		words_not_found = []
		found_word_ids = [int(i['_id']) for i in found_word_objs]
		for k, v in words_map.items() :
			if not v :
				words_not_found.append(k)
		db.index_words.update_many({'_id': {'$in': found_word_ids}}, {'$inc': {'freq': int(1)}}, session = session)
		current_word_count = db.index_words.count_documents({}, session = session)
		if words_not_found :
			new_word_objs = [{'_id': int(i + current_word_count), 'freq': int(1), 'word': w} for i, w in enumerate(words_not_found)]
			new_word_ids = [int(i['_id']) for i in new_word_objs]
			db.index_words.insert_many(new_word_objs, session = session)
			all_words = [i | 0x80000000 for i in found_word_ids + new_word_ids]
		else :
			all_words = [i | 0x80000000 for i in found_word_ids]
		return all_words
