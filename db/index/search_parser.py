
import re

from db import db
from .textseg import cut_for_index
import sys

from utils.exceptions import UserError

def _prefix_fallthrough(words) :
	if not words :
		return [], 'empty'
	print('Using _prefix_fallthrough', file = sys.stderr)
	words_escaped = [re.escape(i) for i in words]
	found_prefix_word_objs = [db.index_words.find({'word': {'$regex': f'^{word_escaped}.*'}}) for word_escaped in words_escaped] # TODO: replace with aggregate $facet
	print('founded prefixs:', found_prefix_word_objs, file = sys.stderr)
	ans = []
	for match_prefix_objs in found_prefix_word_objs :
		if match_prefix_objs :
			word_ids = [int(i['_id']) | 0x80000000 for i in match_prefix_objs]
			if word_ids :
				ans.append({'tags': {'$in': word_ids}})
	if not ans :
		return ans, 'empty'
	if len(ans) == 1 :
		return ans[0]['tags']['$in'], 'any-tags'
	all_single_tag = True
	for item in ans :
		if len(item['tags']['$in']) > 1 :
			all_single_tag = False
			break
	if all_single_tag :
		ans2 = []
		for item in ans :
			ans2.append(item['tags']['$in'])
		return ans2, 'all-tags'
	return ans, 'complex-query'

def parse_search(txt) :
	#if len(txt) <= 2 :
	#    return {}
	words = cut_for_index(txt)
	print(words, file = sys.stderr)
	if not words :
		raise UserError('NO_MATCH_FOUND')
	found_word_objs = list(db.index_words.find({'word': {'$in': words}}))
	words_map = {w: False for w in words}
	for found_word_obj in found_word_objs :
		words_map[found_word_obj['word']] = True
	words_not_found = []
	for k, v in words_map.items() :
		if not v :
			words_not_found.append(k)
	prefix_word_query_objs, prefix_type = _prefix_fallthrough(words_not_found)
	direct_word_ids = [int(i['_id']) | 0x80000000 for i in found_word_objs]
	if prefix_type != 'empty' :
		if direct_word_ids :
			if prefix_type == 'any-tags' :
				return {'tags': {'$all': direct_word_ids, '$in': prefix_word_query_objs}}, 'complex-query'
			elif prefix_type == 'all-tags' :
				merged = direct_word_ids + prefix_word_query_objs
				if len(merged) == 1 :
					return {'tags': merged[0]}, 'single-tag'
				else :
					return {'tags': {'$all': direct_word_ids + prefix_word_query_objs}}, 'all-tags'
			else :
				return {'$and': [{'tags': {'$all': direct_word_ids}}, prefix_word_query_objs]}, 'complex-query'
		else :
			if prefix_type == 'any-tags' :
				if len(prefix_word_query_objs) == 1 :
					return {'tags': prefix_word_query_objs[0]}, 'single-tag'
				else :
					return {'tags': {'$in': prefix_word_query_objs}}, 'any-tags'
			elif prefix_type == 'all-tags' :
				if len(prefix_word_query_objs) == 1 :
					return {'tags': prefix_word_query_objs[0]}, 'single-tag'
				else :
					return {'tags': {'$all': prefix_word_query_objs}}, 'all-tags'
			else :
				return prefix_word_query_objs, 'complex-query'
	else :
		if len(direct_word_ids) == 1 :
			return {'tags': direct_word_ids[0]}, 'single-tag'
		else :
			return {'tags': {'$all': direct_word_ids}}, 'all-tags'
