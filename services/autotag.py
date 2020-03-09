
from db import tagdb as db
from db import client
from db.TagDB_language import translateTagToPreferredLanguage
from utils.dbtools import MongoTransaction, MongoTransactionDisabled
from utils.logger import log
from collections import defaultdict
from db.index.textseg import cut_for_search

import ahocorasick
import itertools

_keyword_dict = None
_automata = None

def buildKeywordDictMongo() :
	"""
	Build keyword dict from scratch and store into MongoDB, manually triggered
	"""
	word_id_map = {}
	def add_words(words, tagid) :
		for w in words :
			if w in word_id_map :
				continue
			else :
				word_id_map[w] = len(word_id_map) + 1
		word_ids = [word_id_map[w] for w in words]
		wordstr = ''.join([chr(wid) for wid in word_ids])
		wordstr_tag_map[wordstr] = tagid
	wordstr_tag_map = {}
	with MongoTransactionDisabled(client) as s :
		db.db.tag_words.delete_many({}, session = s())
		db.db.wordstr_tag.delete_many({}, session = s())
		for tag_obj in db.db.tags.find() :
			for (_, value) in tag_obj['languages'].items() :
				words = cut_for_search(value)
				add_words(words, tag_obj['id'])
				add_words([value], tag_obj['id'])
			for value in tag_obj['alias'] :
				words = cut_for_search(value)
				add_words(words, tag_obj['id'])
				add_words([value], tag_obj['id'])
		for (word, wid) in word_id_map.items() :
			db.db.tag_words.insert_one({'word': word, 'id': wid}, session = s())
		for (wordstr, tagid) in wordstr_tag_map.items() :
			db.db.wordstr_tag.insert_one({'wordstr': wordstr, 'tagid': tagid}, session = s())
		s.mark_succeed()

def buildKeywordDict() :
	"""
	Build keyword dict from data stored in MongoDB, triggered if _keyword_dict is None
	"""
	global _keyword_dict
	ret = db.db.tag_words.find({})
	_keyword_dict = {obj['word']: obj['id'] for obj in ret}

def buildAutomata() :
	ret = db.db.wordstr_tag.find({})
	global _automata
	_automata = ahocorasick.Automaton()
	[_automata.add_word(obj['wordstr'], obj['tagid']) for obj in ret]
	_automata.make_automaton()

def inferTagidsFromText(text) :
	global _keyword_dict
	global _automata
	if _keyword_dict is None :
		buildKeywordDict()
	if _automata is None :
		buildAutomata()
	words = cut_for_search(text)
	word_ids = [_keyword_dict.get(word, 0) for word in words]
	wordstr = ''.join([chr(wid) for wid in word_ids])
	tagids = []
	for _, tagid in _automata.iter(wordstr) :
		tagids.append(tagid)
	return list(set(tagids))

def inferTagsFromVideo(utags, title, desc, user_language) :
	log(obj = {'title': title, 'desc': desc, 'utags': utags, 'lang': user_language})
	utags = [u.lower() for u in utags]
	utags.append(title)
	utags.append(desc)
	all_text = ' 3e7dT2ibT7dM '.join(utags)
	tagids = inferTagidsFromText(all_text)
	return db.translate_tag_ids_to_user_language(tagids, user_language)[0]

