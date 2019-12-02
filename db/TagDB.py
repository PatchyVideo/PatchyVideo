from datetime import datetime
from utils.exceptions import UserError

import re

if __name__ == '__main__':
	from flask_pymongo import PyMongo
	from flask import Flask
	from query_parser import Parser
	from bson import ObjectId
	from collections import defaultdict
	from AutocompleteInterface import AutocompleteInterface
else:
	from .query_parser import Parser
	from bson import ObjectId
	from collections import defaultdict
	from .AutocompleteInterface import AutocompleteInterface

def _diff(old_tags, new_tags):
	old_tags_set = set(old_tags)
	new_tags_set = set(new_tags)
	added_tags = new_tags_set - old_tags_set
	removed_tags = (new_tags_set ^ old_tags_set) - added_tags
	return list(added_tags), list(removed_tags)

class TagDB():
	def __init__(self, db):
		self.db = db
		self.aci = AutocompleteInterface()
		
	def init_autocomplete(self) :
		all_tags = self.db.tags.find({'dst' : {'$exists' : False}})
		all_alias = self.db.tags.find({'dst' : {'$exists' : True}})
		tags_tuple = [(item['tag'], item['category'], item['count']) for item in all_tags]
		alias_tuple = [(item['tag'], item['dst'], item['type']) for item in all_alias]
		self.aci.AddTags(tags_tuple)
		self.aci.AddAlias(alias_tuple)

	def add_category(self, category, user = '', session = None):
		cat = self.db.cats.find_one({'name': category}, session = session)
		if cat is not None:
			raise UserError("CATEGORY_EXIST")
		self.db.cats.insert_one({'name': category, 'count': 0, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session)

	def list_categories(self, session = None):
		ans = []
		for item in self.db.cats.find({}, session = session):
			ans.append(item)
		return ans

	def list_category_tags(self, category, session = None):
		cat = self.db.cats.find_one({'name': category}, session = session)
		if cat is None:
			raise UserError("CATEGORY_NOT_EXIST")
		ans = self.db.tags.find({'category': category, 'type': {'$ne': 'language'}}, session = session)
		return ans

	"""
	def transfer_category(self, tag, new_category, user = '', session = None):
		cat = self.db.cats.find_one({'name': new_category}, session = session)
		if cat is None:
			return 'CATEGORY_NOT_EXIST'
		tag_obj = self.db.tags.find_one({'tag': tag}, session = session)
		if tag_obj is None:
			return 'TAG_NOT_EXIST'
		self.db.tags.update_one({'_id': tag_obj['_id']}, {'$set': {'category': new_category, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		self.db.cats.update_one({'name': cat['name']}, {'$inc': {'count': -1}}, session = session)
		self.db.cats.update_one({'name': new_category}, {'$inc': {'count': 1}}, session = session)
		return 'SUCCEED'
	"""

	def add_tag(self, tag, category, language, user = '', session = None):
		cat = self.db.cats.find_one({'name': category}, session = session)
		if cat is None:
			raise UserError("CATEGORY_NOT_EXIST")
		tag_obj = self.db.tags.find_one({'tag': tag}, session = session)
		if tag_obj is not None:
			raise UserError("TAG_EXIST")
		self.db.tags.insert_one({'category': category, 'language': language, 'tag': tag, 'meta': {'created_by': user, 'created_at': datetime.now()}, 'count': 0}, session = session)
		self.db.cats.update_one({'name': category}, {'$inc': {'count': 1}}, session = session)
		self.aci.AddTags([(tag, category, 0)])

	def find_tags_wildcard(self, query, category) :
		assert isinstance(query, str)
		query = re.escape(query)
		query = query.replace('\\*', '.*')
		query = f'^{query}$'
		if category :
			return self.db.tags.find({'type': {'$ne': 'language'}, 'tag': {'$regex': query}, 'category': category})
		else :
			return self.db.tags.find({'type': {'$ne': 'language'}, 'tag': {'$regex': query}})

	def find_tags_regex(self, query, category) :
		assert isinstance(query, str)
		if category :
			return self.db.tags.find({'type': {'$ne': 'language'}, 'tag': {'$regex': query}, 'category': category})
		else :
			return self.db.tags.find({'type': {'$ne': 'language'}, 'tag': {'$regex': query}})

	def filter_tags(self, tags, session = None):
		found = self.db.tags.aggregate([
			{'$match':{'tag':{'$in':tags}}},
			{'$project':{'tag':1}}], session = session)
		return [item['tag'] for item in found]

	def remove_tag(self, tag_name_or_tag_obj, user = '', session = None):
		tt, tag_obj = self._tag_type(tag_name_or_tag_obj, session = session)
		if tt == 'tag' or tt == 'alias':
			tag = tag_obj['tag']
			self.db.tags.update_many({'dst': tag}, {'$unset': {'dst': '', 'type': '', 'language': ''}, '$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
			self.db.tags.delete_one({'_id': tag_obj['_id']}, session = session)
			self.db.cats.update_one({'name': tag_obj['category']}, {'$inc': {'count': -1}}, session = session)
			self.db.items.update_many({'tags': {'$in': [tag]}}, {'$pull': {'tags': tag}}, session = session)
			# if an alias being deleted, check if it is a language alias
			if 'type' in tag_obj and tag_obj['type'] == 'language' :
				dst_tag_obj = self.db.tags.find_one({'tag': tag_obj['dst']}, session = session)
				assert dst_tag_obj
				assert 'languages' in dst_tag_obj
				language = ''
				# find the language corresponding to the tag being removed
				for (lang, corresponding_tag) in dst_tag_obj['languages'].items() :
					if corresponding_tag == tag :
						language = lang
						break
				assert language
				# remove it
				self.db.tags.update_one({'_id': dst_tag_obj['_id']}, {'$unset': {f'languages.{language}': ''}}, session = session)
			self.aci.DeleteTagOrAlias(tag)
		else:
			raise UserError('TAG_NOT_EXIST')

	def rename_tag(self, tag_name_or_tag_obj, new_tag, user = None, session = None):
		tt, tag_obj = self._tag_type(tag_name_or_tag_obj, session = session)
		if tt == 'tag' or tt == 'alias':
			tag = tag_obj['tag']
			tag_obj2 = self.db.tags.find_one({'tag': new_tag}, session = session)
			if tag_obj2 is not None:
				raise UserError('TAG_EXIST')
			self.db.tags.update_one({'_id': tag_obj['_id']}, {'$set': {'tag': new_tag, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
			self.db.tags.update_many({'dst': tag}, {'$set': {'dst': new_tag, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
			self.db.items.update_many({'tags': {'$in': [tag]}}, {'$set': {'tags.$': new_tag}}, session = session)
			# if an alias being renamed, check if it is a language alias
			if 'type' in tag_obj and tag_obj['type'] == 'language' :
				dst_tag_obj = self.db.tags.find_one({'tag': tag_obj['dst']}, session = session)
				assert dst_tag_obj
				assert 'languages' in dst_tag_obj
				language = ''
				# find the language corresponding to the tag being removed
				for (lang, corresponding_tag) in dst_tag_obj['languages'].items() :
					if corresponding_tag == tag :
						language = lang
						break
				assert language
				# remove it
				self.db.tags.update_one({'_id': dst_tag_obj['_id']}, {'$set': {f'languages.{language}': new_tag}}, session = session)
			self.aci.DeleteTagOrAlias(tag)
			if tt == 'tag' :
				self.aci.AddTags([(new_tag, tag_obj['category'], tag_obj['count'])])
			elif tt == 'alias' :
				self.aci.AddAlias([(new_tag, tag_obj['dst'], tag_obj['type'])])
		else:
			raise UserError('TAG_NOT_EXIST')

	def retrive_items(self, tag_query, session = None):
		return self.db.items.find(tag_query, session = session)

	def retrive_item(self, tag_query_or_item_id, session = None):
		if isinstance(tag_query_or_item_id, ObjectId):
			return self.db.items.find_one({'_id': ObjectId(tag_query_or_item_id)}, session = session)
		else:
			return self.db.items.find_one(tag_query_or_item_id, session = session)

	def retrive_tags(self, item_id, session = None):
		item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None:
			raise UserError('ITEM_NOT_EXIST')
		return item['tags']

	def retrive_item_tags_with_category(self, item_id, session = None):
		item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None:
			raise UserError('ITEM_NOT_EXIST')
		tag_objs = self.db.tags.find({'tag': {'$in': item['tags']}}, session = session)
		ans = defaultdict(list)
		for obj in tag_objs:
			ans[obj['category']].append(obj['tag'])
		return ans

	def get_tag_category(self, tags, session = None):
		tag_objs = self.db.tags.find({'tag': {'$in': tags}}, session = session)
		ans = defaultdict(list)
		for obj in tag_objs:
			ans[obj['category']].append(obj['tag'])
		return ans

	def get_tag_category_map(self, tags, session = None):
		tag_objs = self.db.tags.find({'tag': {'$in': tags}}, session = session)
		ans = {}
		for obj in tag_objs:
			ans[obj['tag']] = obj['category']
		return ans

	def add_item(self, tags, item, user = '', session = None):
		item_id = self.db.items.insert_one({'tags': tags, 'item': item, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session).inserted_id
		self.db.tags.update_many({'tag': {'$in': tags}}, {'$inc': {'count': 1}}, session = session)
		self.aci.SetTagOrAliasCountDiff([(t, 1) for t in tags])
		return item_id

	def verify_tags(self, tags, session = None):
		found_tags = self.db.tags.find({'tag': {'$in': tags}}, session = session)
		tm = []
		for tag in found_tags:
			tm.append(tag['tag'])
		for tag in tags:
			if not tag in tm:
				raise UserError('TAG_NOT_EXIST', tag)

	def update_item(self, item_id, item, user = '', session = None):
		item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None:
			raise UserError('ITEM_NOT_EXIST')
		self.db.items.update_one({'_id': ObjectId(item_id)}, {'$set': {'item': item, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

	def update_item_query(self, item_id_or_item_object, query, user = '', session = None):
		"""
		Your update query MUST NOT modify tags
		"""
		if isinstance(item_id_or_item_object, ObjectId) or isinstance(item_id_or_item_object, str):
			item = self.db.items.find_one({'_id': ObjectId(item_id_or_item_object)}, session = session)
			if item is None:
				raise UserError('ITEM_NOT_EXIST')
		else:
			item = item_id_or_item_object
		self.db.items.update_one({'_id': ObjectId(item['_id'])}, query, session = session)
		self.db.items.update_one({'_id': ObjectId(item['_id'])}, {'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

	def update_item_tags(self, item_id_or_item_object, new_tags, user = '', session = None):
		if isinstance(item_id_or_item_object, ObjectId) or isinstance(item_id_or_item_object, str):
			item = self.db.items.find_one({'_id': ObjectId(item_id_or_item_object)}, session = session)
			if item is None:
				raise UserError('ITEM_NOT_EXIST')
		else:
			item = item_id_or_item_object
		self.db.tags.update_many({'tag': {'$in': item['tags']}}, {'$inc': {'count': -1}}, session = session)
		self.db.tags.update_many({'tag': {'$in': new_tags}}, {'$inc': {'count': 1}}, session = session)
		self.aci.SetTagOrAliasCountDiff([(t, -1) for t in item['tags']])
		self.aci.SetTagOrAliasCountDiff([(t, 1) for t in new_tags])
		self.db.items.update_one({'_id': ObjectId(item['_id'])}, {'$set': {'tags': new_tags, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

	def _get_many_tag_counts(self, item_ids = None, tags = None, user = '', session = None):
		id_match_obj = { '_id' : { '$in': item_ids } } if item_ids else {}
		tag_match_obj = { '_id' : { '$in' : tags } } if tags else {}
		return self.db.items.aggregate([
		{
			"$match" : id_match_obj
		},
		{
			"$project" : { "tags" : 1 }
		},
		{
			"$unwind" : { "path" : "$tags" }
		},
		{
			"$group" : { "_id" : "$tags", "count" : { "$sum" : 1 } }
		},
		{
			"$match" : tag_match_obj
		}
		], session = session)

	def update_many_items_tags_merge(self, item_ids, new_tags, user = '', session = None):
		prior_tag_counts = dict([(item['_id'], item['count']) for item in self._get_many_tag_counts(item_ids, new_tags, user, session)])
		self.db.items.update_many({'_id': {'$in': item_ids}}, {
			'$addToSet': {'tags': {'$each': new_tags}},
			'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		num_items = len(item_ids)
		new_tag_count_diff = [(tag, num_items - prior_tag_counts.get(tag, 0)) for tag in new_tags]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'tag': tag}, {'$inc': {'count': diff}}, session = session) # $inc is atomic, no locking needed
		self.aci.SetTagOrAliasCountDiff(new_tag_count_diff)

	def update_many_items_tags_pull(self, item_ids, tags_to_remove, user = '', session = None):
		prior_tag_counts = dict([(item['_id'], item['count']) for item in self._get_many_tag_counts(item_ids, tags_to_remove, user, session)])
		self.db.items.update_many({'_id': {'$in': item_ids}}, {
			'$pullAll': {'tags': tags_to_remove},
			'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		new_tag_count_diff = [(tag, -prior_tag_counts.get(tag, 0)) for tag in tags_to_remove]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'tag': tag}, {'$inc': {'count': diff}}, session = session)
		self.aci.SetTagOrAliasCountDiff(new_tag_count_diff)

	def update_item_tags_merge(self, item_id, new_tags, user = '', session = None):
		prior_tag_counts = dict([(item['_id'], item['count']) for item in self._get_many_tag_counts([item_id], new_tags, user, session)])
		item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None :
			raise UserError('ITEM_NOT_EXIST')
		self.db.items.update_one({'_id': ObjectId(item_id)}, {
			'$addToSet': {'tags': {'$each': new_tags}},
			'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		new_tag_count_diff = [(tag, 1 - prior_tag_counts.get(tag, 0)) for tag in new_tags]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'tag': tag}, {'$inc': {'count': diff}}, session = session)
		self.aci.SetTagOrAliasCountDiff(new_tag_count_diff)

	def update_item_tags_pull(self, item_id, tags_to_remove, user = '', session = None):
		prior_tag_counts = dict([(item['_id'], item['count']) for item in self._get_many_tag_counts([item_id], tags_to_remove, user, session)])
		item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None :
			raise UserError('ITEM_NOT_EXIST')
		self.db.items.update_one({'_id': ObjectId(item_id)},  {
			'$pullAll': {'tags': tags_to_remove},
			'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		new_tag_count_diff = [(tag, -prior_tag_counts.get(tag, 0)) for tag in tags_to_remove]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'tag': tag}, {'$inc': {'count': diff}}, session = session)
		self.aci.SetTagOrAliasCountDiff(new_tag_count_diff)

	def update_tag_language(self, tag, language, user = '', session = None):
		tt, tag_obj = self._tag_type(tag, session = session)
		if not tt :
			raise UserError('TAG_NOT_EXIST')
		if tt != 'tag' :
			raise UserError('NOT_TAG')
		if 'languages' in tag_obj and language in tag_obj['languages'] :
			self.db.tags.update_one({'tag': tag_obj['languages'][language]}, {'$set': {'type': 'regular'}}, session = session)
			self.db.tags.update_one({'_id': tag_obj['_id']}, {'$unset': {f'languages.{language}': ''}}, session = session)
		self.db.tags.update_one({'_id': tag_obj['_id']}, {'$set': {'language': language}}, session = session)

	def add_tag_alias(self, src_tag, dst_tag, alias_type, language = '', user = '', session = None):
		if dst_tag == src_tag :
			raise UserError('SAME_TAG')
		assert alias_type in ['regular', 'language']
		tt_dst, tag_obj_dst = self._tag_type(dst_tag, session = session)
		tt_src, tag_obj_src = self._tag_type(src_tag, session = session)
		if tt_dst == 'tag':
			if tt_src == 'tag':
				alias_obj = self.db.tags.find_one({'tag': src_tag, 'dst': dst_tag}, session = session)
				if alias_obj is not None:
					raise UserError('ALIAS_EXIST')
				dupilcated_tags_count = self.db.items.count_documents({'tags': {'$all': [src_tag, dst_tag]}}, session = session)
				src_post_count = tag_obj_src['count']
				if alias_type == 'regular' :
					self.db.tags.update_one({'_id': ObjectId(tag_obj_src['_id'])}, {'$set': {
						'count': 0,
						'language': language or tag_obj_dst['language'],
						'dst': dst_tag,
						'type': 'regular',
						'meta.modified_by': user,
						'meta.modified_at': datetime.now()
						}}, session = session)
				elif alias_type == 'language' :
					assert len(language) > 0
					if 'language' in tag_obj_dst and tag_obj_dst['language'] == language :
						# root tag has the same language as the one user is trying to add
						raise UserError('LANGUAGE_EXIST')
					self.db.tags.update_one({'_id': ObjectId(tag_obj_src['_id'])}, {'$set': {
						'count': 0,
						'dst': dst_tag,
						'type': 'language',
						'language' : language,
						'meta.modified_by': user,
						'meta.modified_at': datetime.now()
						}}, session = session)
				self.db.tags.update_many({'dst': src_tag}, {'$set': {'dst': dst_tag, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
				self.db.tags.update_one({'_id': ObjectId(tag_obj_dst['_id'])}, {'$inc': {'count': src_post_count - dupilcated_tags_count}}, session = session)
				if alias_type == 'language' :
					if 'languages' not in tag_obj_dst :
						self.db.tags.update_one({'_id': ObjectId(tag_obj_dst['_id'])}, {'$set': {'languages': {language: src_tag}}}, session = session)
					else :
						if language in tag_obj_dst['languages'] :
							# overwriting an existing language tag
							# change old tag type to regular
							self.db.tags.update_one({'_id': ObjectId(tag_obj_src['_id'])}, {'$set': {'type': 'regular'}}, session = session)
						self.db.tags.update_one({'_id': ObjectId(tag_obj_dst['_id'])}, {'$set': {f'languages.{language}': src_tag}}, session = session)
				self.db.items.update_many({'tags': {'$in': [src_tag]}}, {'$addToSet': {'tags': dst_tag}}, session = session)
				self.db.items.update_many({'tags': {'$in': [src_tag]}}, {'$pullAll': {'tags': [src_tag]}}, session = session)
				self.aci.AddAlias([(src_tag, dst_tag, alias_type)])
				self.aci.SetTagOrAliasCountDiff([(dst_tag, src_post_count - dupilcated_tags_count)])
			elif tt_src == 'alias':
				# overwriting an existing alias
				# step 1: remove it
				self.remove_tag_alias(src_tag, user, session)
				# step 2: add it
				return self.add_tag_alias(src_tag, dst_tag, alias_type, language, user, session)
			else:
				# if src tag not exist, add one
				self.add_tag(src_tag, tag_obj_dst['category'], language or tag_obj_dst['language'], user, session)
				self.add_tag_alias(src_tag, dst_tag, alias_type, language, user, session)
		elif tt_dst == 'alias':
			self.add_tag_alias(src_tag, tag_obj_dst['dst'], user, session = session)
		else:
			raise UserError('TAG_NOT_EXIST')

	def remove_tag_alias(self, src_tag, user = '', session = None):
		tt, tag_obj = self._tag_type(src_tag, session = session)
		if tt == 'tag':
			raise UserError('NOT_ALIAS')
		elif tt == 'alias':
			dst_tag = tag_obj['dst']
			self.db.tags.update_one({'_id': tag_obj['_id']}, {'$unset': {'dst': '', 'type': ''}}, session = session)
			if 'type' in tag_obj and tag_obj['type'] == 'language' :
				dst_tag_obj = self.db.tags.find_one({'tag': dst_tag}, session = session)
				assert dst_tag_obj
				assert 'languages' in dst_tag_obj
				language = ''
				# find the language corresponding to the alias being removed
				for (lang, corresponding_tag) in dst_tag_obj['languages'].items() :
					if corresponding_tag == src_tag :
						language = lang
						break
				assert language
				# remove it
				self.db.tags.update_one({'_id': dst_tag_obj['_id']}, {'$unset': {f'languages.{language}': ''}}, session = session)
			self.aci.DeleteAlias(src_tag)
		else:
			raise UserError('ALIAS_NOT_EXIST')

	def translate_tags(self, tags, session = None):
		src_tag_objs = self.db.tags.find({'tag': {'$in': tags}, 'dst': {'$exists': True}}, session = session)
		tag_map = {}
		for item in src_tag_objs:
			tag_map[item['tag']] = item['dst']
		return [tag_map[tag] if tag in tag_map else tag for tag in tags]

	"""
	def count_items(self, tag_query, session = None):
		pass

	def count_items_tag(self, tag, session = None):
		pass
	"""

	def add_tag_group(self, group_name, tags = [], user = '', session = None):
		g_obj = self.db.groups.find_one({'name': group_name}, session = session)
		if g_obj is not None:
			raise UserError('GROUP_EXIST')
		self.db.groups.insert_one({'name': group_name, 'tags': tags, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session)

	def remove_tag_group(self, group_name, user = '', session = None):
		g_obj = self.db.groups.find_one({'name': group_name}, session = session)
		if g_obj is None:
			raise UserError('GROUP_NOT_EXIST')
		self.db.groups.remove({'name': group_name}, session = session)

	def list_tag_group(self, group_name, session = None):
		g_obj = self.db.groups.find_one({'name': group_name}, session = session)
		if g_obj is None:
			raise UserError('GROUP_NOT_EXIST')
		return g_obj['tags']

	def update_tag_group(self, group_name, new_tags, user = '', session = None):
		g_obj = self.db.groups.find_one({'name': group_name}, session = session)
		if g_obj is None:
			raise UserError('GROUP_NOT_EXIST')
		self.db.groups.update_one({'name': group_name}, {'$set': {'tags': new_tags, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

	def translate_tag_group(self, groups, session = None):
		gm = {}
		g_objs = self.db.groups.find({'name': {'$in': groups}}, session = session)
		for g_obj in g_objs:
			gm[g_obj['name']] = g_obj['tags']
		for g in groups:
			if not g in gm:
				gm[g] = []
		return gm

	def translate_tag_wildcard(self, query) :
		query = re.escape(query)
		query = query.replace('\\*', '.*')
		query = f'^{query}$'
		ret = self.db.tags.aggregate([
		{
			'$match' : {
				'tag' : {'$regex' : query}
			}
		},
		{
			'$project' : {
				'tag' : 1
			}
		}])
		return [item['tag'] for item in ret]

	# TODO: ....
	def compile_query(self, query, session = None):
		query_obj, tags = Parser.parse(query, self.translate_tags, self.translate_tag_group, self.translate_tag_wildcard)
		if query_obj is None:
			raise UserError('INCORRECT_QUERY')
		return query_obj, tags

	def _tag_type(self, tag_name_or_tag_obj, session = None):
		if isinstance(tag_name_or_tag_obj, dict) :
			if 'dst' in tag_name_or_tag_obj :
				return 'alias', tag_name_or_tag_obj
			else :
				return 'tag', tag_name_or_tag_obj
		tag_obj = self.db.tags.find_one({'tag': tag_name_or_tag_obj}, session = session)
		if tag_obj is None:
			return None, None
		if 'dst' in tag_obj:
			return 'alias', tag_obj
		else:
			return 'tag', tag_obj

	def _check_tag_name(self, tag, session = None):
		return True

