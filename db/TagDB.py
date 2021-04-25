from datetime import datetime
from utils.exceptions import UserError
from collections import deque
from bson.json_util import dumps

import re

if __name__ == '__main__':
	from flask_pymongo import PyMongo
	from flask import Flask
	from query_parser import Parser
	from bson import ObjectId
	from collections import defaultdict
	from AutocompleteInterface import AutocompleteInterface, AutocompleteInterfaceDummy
	from TagDB_language import VALID_LANGUAGES, PREFERRED_LANGUAGE_MAP, translateTagToPreferredLanguage
else:
	from .query_parser import Parser
	from bson import ObjectId
	from collections import defaultdict
	from .AutocompleteInterface import AutocompleteInterface, AutocompleteInterfaceDummy
	from .TagDB_language import VALID_LANGUAGES, PREFERRED_LANGUAGE_MAP, translateTagToPreferredLanguage
	from .index.search_parser import parse_search
	from .index.index_builder import build_index, remove_index, remove_index_from_text


"""
db.categories:
{
	"_id": ...,
	"color": "#0073ff",
	"name": "Copyright" // other languages will be handled by the frontend
}

db.tags:
{
	"_id": ...,
	"category": "Copyright",
	"count": 114514,
	"icon": "<filename>",
	"languages": {
		"CHS": "东方",
		"ENG": "touhou",
		...
	},
	"alias": [
		"toho",
		...
	]
}

db.tag_alias:
{
	"_id": ...,
	"tag": "东方",
	"dst": ObjectId("...")
}

db.tag_history:
{
	"_id": ...
	"vid": ObjectId("..."),
	"time": ...,
	"user": ObjectId("..."),
	"add": [...],
	"del": [...],
	"tags: [...]
}
"""

_CATEGORY_MAP = {
	'General': 0,
	'Character': 1,
	'Copyright': 2,
	'Author': 3,
	'Meta': 4,
	'Language': 5,
	'Soundtrack': 6
}

def _diff(old_tags, new_tags):
	old_tags_set = set(old_tags)
	new_tags_set = set(new_tags)
	added_tags = new_tags_set - old_tags_set
	removed_tags = (new_tags_set ^ old_tags_set) - added_tags
	return list(added_tags), list(removed_tags)

class TagDB() :
	def __init__(self, db, db_name = 'videos', use_aci = True) :
		self.db = db
		if use_aci :
			self.aci = AutocompleteInterface()
		else :
			self.aci = AutocompleteInterfaceDummy()
		self.db_name = db_name

	def aggregate(self, *args, **kwargs) :
		return self.db[self.db_name].aggregate(*args, **kwargs)
	
	def init_autocomplete(self) :
		all_tags = [i for i in self.db.tags.find()]
		tags_tuple = [(item['id'], item['count'], _CATEGORY_MAP[item['category']]) for item in all_tags]
		words_tuple = deque([])
		for tag_obj in all_tags :
			for (lang, word) in tag_obj['languages'].items() :
				words_tuple.append((tag_obj['id'], word, lang))
			for alias in tag_obj['alias'] :
				words_tuple.append((tag_obj['id'], alias, "NAL"))
		self.aci.AddTag(tags_tuple)
		self.aci.AddWord(words_tuple)
	
	def add_category(self, category, color = '#000', user = '', session = None) :
		cat = self.db.cats.find_one({'name': category}, session = session)
		if cat is not None:
			raise UserError("CATEGORY_ALREADY_EXIST")
		self.db.cats.insert_one({'name': category, 'count': 0, 'color': color, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session)

	def list_categories(self, session = None) :
		return [item for item in self.db.cats.find({}, session = session)]

	def list_category_tags(self, category, blacklist_tagids = [], session = None) :
		self._check_category(category, session)
		ans = self.db.tags.find({'$and': [{'category': category}, {'id': {'$nin': blacklist_tagids}}]}, session = session)
		return ans

	def transfer_category(self, tag, new_category, user = '', session = None) :
		cat = self._check_category(new_category, session)
		tag_obj = self._tag(tag, session = session)
		self.db.tags.update_one({'_id': tag_obj['_id']}, {'$set': {'category': new_category, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		self.db.cats.update_one({'name': cat['name']}, {'$inc': {'count': -1}}, session = session)
		self.db.cats.update_one({'name': new_category}, {'$inc': {'count': 1}}, session = session)
		self.aci.SetCat([(tag_obj['id'], _CATEGORY_MAP[new_category])])

	def _get_free_tag_id(self, session) :
		obj = self.db.free_tags.find_one()
		if obj is None :
			try :
				return self.db.tags.count_documents({}, session = session)
			except Exception as ex:
				print(ex)
				return 0
		else :
			self.db.free_tags.delete_one({'id': obj['id']})
			return obj['id']
	
	def add_tag(self, tag, category, language, user = '', session = None) :
		self._check_language(language)
		self._check_category(category, session)
		tag_obj = self._tag(tag, return_none = True, session = session)
		if tag_obj is not None :
			raise UserError('TAG_ALREADY_EXIST')
		tag_id = self._get_free_tag_id(session)
		item_id = self.db.tags.insert_one({
			'id': tag_id,
			'category': category,
			'count': 0,
			'icon': '',
			'languages': {language: tag},
			'alias': [],
			'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
		}, session = session).inserted_id
		self.db.tag_alias.insert_one({
			'tag': tag,
			'dst': item_id,
			'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
		}, session = session)
		self.db.cats.update_one({'name': category}, {'$inc': {'count': 1}}, session = session)
		self.aci.AddTag([(tag_id, 0, _CATEGORY_MAP[category])])
		self.aci.AddWord([(tag_id, tag, language)])
		return tag_id

	def find_tags_wildcard(self, query, category, offset, limit, order, blacklist_tagids = []) :
		assert isinstance(query, str)
		query = query.strip()
		if ' ' in query :
			querys = query.split(' ')
			querys = ['.*' + re.escape(q) + '.*' for q in querys if q]
			query = '^' + '|'.join(querys) + '$'
		else :
			query = re.escape(query)
			#query = query.replace('\\*', '.*')
			query = f'^.*{query}.*$'
		return self.find_tags_regex(query, category, offset, limit, order, blacklist_tagids)

	def find_tags_regex(self, query, category, offset, limit, order, blacklist_tagids = []) :
		assert isinstance(query, str)
		if category :
			match_obj = {'$and': [{'category': category}, {'id': {'$nin': blacklist_tagids}}]}
		else :
			match_obj = {'id': {'$nin': blacklist_tagids}}
			
		if order not in ['latest', 'oldest', 'count', 'count_inv'] :
	   		raise UserError('INCORRECT_ORDER')

		if order == 'latest':
			sort_obj = {"meta.created_at": -1}
		if order == 'oldest':
			sort_obj = {"meta.created_at": 1}
		if order == 'count':
			sort_obj = {"count": 1}
		elif order == 'count_inv':
			sort_obj = {"count": -1}

		return self.db.tag_alias.aggregate([
			{'$match': {'tag': re.compile(query, re.IGNORECASE)}},
			{'$group': {'_id': "$dst"}},
			{'$lookup': {'localField': '_id', 'foreignField': '_id', 'from': 'tags', 'as': 'tag'}},
			{'$replaceRoot': {'newRoot': {'$mergeObjects': [{'$arrayElemAt': ["$tag", 0]}, "$$ROOT"]}}},
			{'$project': {'tag': 0}},
			{'$match': match_obj},
			{'$facet':
			{
				'result': [
					{'$sort': sort_obj},
					{'$skip': offset},
					{'$limit': limit}
				],
				'tags_found': [
					{'$count': 'tags_found'}
				]
			}
		}
		])

	def filter_and_translate_tags(self, tags, session = None) :
		if not tags :
			return []
		found = self.db.tag_alias.aggregate([
			{'$match': {'tag': {'$in': tags}}},
			{'$lookup': {"from" : "tags", "localField" : "dst", "foreignField" : "_id", "as" : "tag_obj"}},
			{'$unwind': {'path': '$tag_obj'}},
			{'$project': {'tag_obj.id': 1}}
		], session = session)
		return list(set([item['tag_obj']['id'] for item in found]))

	def _translate_text_search(self, text) :
		if '*' in text : # tag wildcard
			return text
		if text in ['site', 'date', 'placeholder', 'and', 'or', 'not', 'any', 'all', 'tags', 'true', 'false', 'repost'] :
			return text
		serach_obj, serach_type = parse_search(text)
		return ')' + dumps({'obj': serach_obj, 'type': serach_type})

	def translate_tags(self, tags, session = None) :
		tag_alias_objs = self.db.tag_alias.aggregate([
			{'$match': {'tag': {'$in': tags}}},
			{'$lookup': {"from" : "tags", "localField" : "dst", "foreignField" : "_id", "as" : "tag_obj"}},
			{'$unwind': {'path': '$tag_obj'}}
		], session = session)
		tag_map = {}
		for item in tag_alias_objs:
			tag_map[item['tag']] = item['tag_obj']['id']
		return [tag_map[tag] if tag in tag_map else self._translate_text_search(tag) for tag in tags]

	def translate_text(self, terms, session = None) :
		return [self._translate_text_search(term) for term in terms]

	def remove_tag(self, tag_name_or_tag_obj, user = '', session = None) :
		tag_obj = self._tag(tag_name_or_tag_obj, session = session)
		if tag_obj['category'] == 'Author' and 'author' in tag_obj :
			raise UserError('AUTHOR_TAG_DELETION_DISABLED')
		tagid = tag_obj['id']
		self.db.tag_alias.delete_many({'dst': tag_obj['_id']}, session = session)
		self.db.tags.delete_one({'_id': tag_obj['_id']}, session = session)
		self.db.cats.update_one({'name': tag_obj['category']}, {'$inc': {'count': -1}}, session = session)
		history_items = list(self.db[self.db_name].aggregate([
			{'$match': {'tags': {'$in': [tagid]}}},
			{'$project': {'vid': '$_id', 'tags': {'$filter': {'input': '$tags', 'as': 'tag', 'cond': {'$lt': ['$$tag', 0x80000000]}}}}},
			{'$addFields': {'del': [tagid], 'add': [], 'time': datetime.now(), 'user': user}},
			{'$match': {'$or': [{'del': {'$not': {'$size': 0}}}, {'add': {'$not': {'$size': 0}}}]}},
		], session = session))
		if history_items :
			for i in history_items :
				del i['_id']
			if self.db_name == 'videos' :
				self.db.tag_history.insert_many(history_items, session = session)
		self.db[self.db_name].update_many({'tags': {'$in': [tagid]}}, {'$pull': {'tags': tagid}, '$inc': {'tag_count': int(-1)}}, session = session)
		self.db.free_tags.insert_one({'id': tagid})
		self.aci.DeleteTag(tagid)

	def merge_tag(self, tag_name_or_tag_obj_dst, tag_name_or_tag_obj_src, user = '', session = None) :
		tag_obj_dst = self._tag(tag_name_or_tag_obj_dst, session = session)
		tag_obj_src = self._tag(tag_name_or_tag_obj_src, session = session)
		if tag_obj_src['id'] == tag_obj_dst['id'] :
			raise UserError('SAME_TAG')

		self.db[self.db_name].update_many({'tags': {'$in': [tag_obj_src['id']]}}, {
			'$addToSet': {'tags': tag_obj_dst['id']},
			'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

		tmp_func = self.aci.DeleteTag
		self.aci.DeleteTag = lambda x: x
		self.remove_tag(tag_obj_src, user, session = session)
		self.aci.DeleteTag = tmp_func

		new_langs = []
		addtional_alias = []
		for (k, v) in tag_obj_src['languages'].items() :
			if k not in tag_obj_dst['languages'] :
				new_langs.append((k, v))
			else :
				addtional_alias.append(v)
		for (k, v) in new_langs :
			tag_obj_dst['languages'][k] = v
			self.db.tag_alias.insert_one({
				'tag': v,
				'dst': tag_obj_dst['_id'],
				'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
			}, session = session)
		for alias in tag_obj_src['alias'] + addtional_alias :
			tag_obj_dst['alias'].append(alias)
			self.db.tag_alias.insert_one({
				'tag': alias,
				'dst': tag_obj_dst['_id'],
				'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
			}, session = session)

		self.db.tags.replace_one({'_id': tag_obj_dst['_id']}, tag_obj_dst, session = session)
		self.aci.DeleteTag(tag_obj_src['id'])

	def _get_tag_name_reference_count(self, tag_name, tag_obj) :
		ans = 0
		lang = None
		for (k, v) in tag_obj['languages'].items() :
			if v == tag_name :
				ans += 1
				lang = k
		for alias in tag_obj['alias'] :
			if alias == tag_name :
				ans += 1
		return ans, lang

	def add_or_rename_tag(self, tag_name, new_tag_name, language, user = '', session = None) :
		self._check_language(language)
		tag_obj = self._tag(tag_name, session = session)
		new_tag_alias_obj = self.db.tag_alias.find_one({'tag': new_tag_name}, session = session)
		if new_tag_alias_obj is not None and new_tag_alias_obj['dst'] != tag_obj['_id'] :
			raise UserError('TAG_ALREADY_EXIST')
		
		if new_tag_alias_obj is None :
			if not isinstance(tag_name, int) :
				rc, lang_referenced = self._get_tag_name_reference_count(tag_name, tag_obj)
				assert rc > 0
				# if it is only referenced once AND it is exactly referenced by the given language
				# then it is a unique rename operation, we have to delete the old name
				if rc == 1 and lang_referenced == language :
					self.db.tag_alias.update_one({'tag': tag_name}, {
						'$set': {
							'tag': new_tag_name,
							'meta.modified_by': user, 'meta.modified_at': datetime.now()
						}
					}, session = session)
					self.aci.DeleteWord(tag_name)
					self.aci.AddWord([(tag_obj['id'], new_tag_name, language)])
				else :
					self.db.tag_alias.insert_one({
						'tag': new_tag_name,
						'dst': tag_obj['_id'],
						'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
					}, session = session)
					self.aci.AddWord([(tag_obj['id'], new_tag_name, language)])
			else :
				self.db.tag_alias.insert_one({
					'tag': new_tag_name,
					'dst': tag_obj['_id'],
					'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
				}, session = session)
				self.aci.AddWord([(tag_obj['id'], new_tag_name, language)])
		else :
			# since tag_alias already exists for new_tag_name, no need to insert new tag_alias
			# but we need to consider whether or not to delete the old one
			if not isinstance(tag_name, int) :
				rc, lang_referenced = self._get_tag_name_reference_count(tag_name, tag_obj)
				assert rc > 0
				if lang_referenced is None :
					# we have an alias with the same name
					raise UserError('TAG_ALREADY_EXIST')
				# delete ONLY IF it is referenced only once AND it is exactly referenced by the given language
				if rc == 1 and lang_referenced == language and tag_name != new_tag_name :
					self.db.tag_alias.delete_one({'tag': tag_name}, session = session)
					self.aci.DeleteWord(tag_name)
			else :
				rc, lang_referenced = self._get_tag_name_reference_count(new_tag_name, tag_obj)
				assert rc > 0
				if lang_referenced is None :
					# we have an alias with the same name
					raise UserError('TAG_ALREADY_EXIST')

		# add or update tag specified by language
		self.db.tags.update_one({'_id': tag_obj['_id']}, {
			'$set': {
				f'languages.{language}': new_tag_name,
				'meta.modified_by': user, 'meta.modified_at': datetime.now()
			}
		}, session = session)

	def add_or_rename_alias(self, tag_name, alias_name, user = '', session = None) :
		if tag_name == alias_name :
			raise UserError('SAME_NAME')
		old_alias_name = tag_name
		tag_obj = self._tag(tag_name, session = session)
		alias_obj = self.db.tag_alias.find_one({'tag': alias_name}, session = session)
		if alias_obj is not None :
			raise UserError('ALIAS_ALREADY_EXIST')

		if isinstance(tag_name, int) :
			# add
			self.db.tag_alias.insert_one({
				'tag': alias_name,
				'dst': tag_obj['_id'],
				'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
			}, session = session)
			self.db.tags.update_one({'_id': tag_obj['_id']}, {
				'$addToSet': {'alias': alias_name},
			}, session = session)
			self.aci.AddWord([(tag_obj['id'], alias_name, "NAL")])
		else :
			rc, lang_referenced = self._get_tag_name_reference_count(old_alias_name, tag_obj)
			if rc == 1 and lang_referenced is None :
				# rename
				# in such case, tag_name IS old_alias_name
				self.db.tag_alias.update_one({'tag': old_alias_name}, {
				'$set': {
					'tag': alias_name,
					'meta.modified_by': user, 'meta.modified_at': datetime.now()
				}
				}, session = session)
				self.db.tags.update_one({'_id': tag_obj['_id']}, {'$pullAll': {'alias': [old_alias_name]}}, session = session)
				self.db.tags.update_one({'_id': tag_obj['_id']}, {'$addToSet': {'alias': alias_name}}, session = session)
				self.aci.DeleteWord(old_alias_name)
				self.aci.AddWord([(tag_obj['id'], alias_name, "NAL")])
			else :
				# add
				self.db.tag_alias.insert_one({
					'tag': alias_name,
					'dst': tag_obj['_id'],
					'meta': {'created_by': user, 'created_at': datetime.now(), 'modified_by': user, 'modified_at': datetime.now()}
				}, session = session)
				self.db.tags.update_one({'_id': tag_obj['_id']}, {
					'$addToSet': {'alias': alias_name},
				}, session = session)
				self.aci.AddWord([(tag_obj['id'], alias_name, "NAL")])
	
	def retrive_items(self, tag_query, session = None) :
		return self.db[self.db_name].find(tag_query, session = session)

	def retrive_item(self, tag_query_or_item_id, session = None) :
		if isinstance(tag_query_or_item_id, ObjectId) or isinstance(tag_query_or_item_id, str):
			return self.db[self.db_name].find_one({'_id': ObjectId(tag_query_or_item_id)}, session = session)
		else:
			return self.db[self.db_name].find_one(tag_query_or_item_id, session = session)

	"""
	def get_tag_category(self, tags, session = None) :
		found = self.db.tag_alias.aggregate([
			{'$match': {'tag': {'$in': tags}}},
			{'$lookup': {"from" : "tags", "localField" : "dst", "foreignField" : "_id", "as" : "tag_obj"}},
			{'$unwind': {'path': '$tag_obj'}}
		], session = session)
		ans = defaultdict(list)
		for obj in found :
			ans[obj['tag_obj']['category']].append(obj['tag'])
		return ans
	"""

	def get_tag_category_map(self, tags, session = None):
		tag_objs = self.db.tag_alias.aggregate([
			{'$match': {'tag': {'$in': tags}}},
			{'$lookup': {"from" : "tags", "localField" : "dst", "foreignField" : "_id", "as" : "tag_obj"}},
			{'$unwind': {'path': '$tag_obj'}}
		], session = session)
		ans = {}
		for obj in tag_objs:
			ans[obj['tag']] = obj['tag_obj']['category']
		return ans
	
	def translate_tag_ids_to_user_language_map(self, tag_ids, language, session = None) :
		tag_objs = self.db.tags.find({'id': {'$in': tag_ids}}, session = session)
		tagid_to_tag_map = {}
		for obj in tag_objs :
			tag_in_user_language = translateTagToPreferredLanguage(obj, language)
			tagid_to_tag_map[obj['id']] = tag_in_user_language
		return tagid_to_tag_map

	def translate_tag_ids_to_user_language(self, tag_ids, language, session = None, id_data_map = None) :
		tag_objs = self.db.tags.find({'id': {'$in': tag_ids}}, session = session)
		category_tag_map = defaultdict(list)
		tag_category_map = {}
		tags = []
		for obj in tag_objs :
			tag_in_user_language = translateTagToPreferredLanguage(obj, language)
			if id_data_map :
				tags.append((tag_in_user_language, id_data_map[str(obj['id'])]))
			else :
				tags.append(tag_in_user_language)
			category_tag_map[obj['category']].append(tag_in_user_language)
			tag_category_map[tag_in_user_language] = obj['category']
		return tags, category_tag_map, tag_category_map

	def translate_tag_ids_to_user_language_with_count(self, tag_ids, language, session = None) :
		tag_objs = self.db.tags.find({'id': {'$in': tag_ids}}, session = session)
		category_tag_map = defaultdict(list)
		tag_category_map = {}
		tags = []
		for obj in tag_objs :
			tag_in_user_language = translateTagToPreferredLanguage(obj, language)
			tags.append({'tag': tag_in_user_language, 'count': obj['count']})
			category_tag_map[obj['category']].append(tag_in_user_language)
			tag_category_map[tag_in_user_language] = obj['category']
		return tags, category_tag_map, tag_category_map

	def retrive_item_with_tag_category_map(self, tag_query_or_item_id, language, session = None) :
		if isinstance(tag_query_or_item_id, ObjectId) or isinstance(tag_query_or_item_id, str):
			item_obj = self.db[self.db_name].find_one({'_id': ObjectId(tag_query_or_item_id)}, session = session)
		elif isinstance(tag_query_or_item_id, dict) :
			item_obj = tag_query_or_item_id
		else:
			item_obj = self.db[self.db_name].find_one(tag_query_or_item_id, session = session)
		if item_obj is None :
			raise UserError('ITEM_NOT_EXIST')
		tag_objs = self.db.tags.find({'id': {'$in': item_obj['tags']}}, session = session)
		category_tag_map = defaultdict(list)
		tag_category_map = {}
		tags = []
		for obj in tag_objs :
			tag_in_user_language = translateTagToPreferredLanguage(obj, language)
			tags.append(tag_in_user_language)
			category_tag_map[obj['category']].append(tag_in_user_language)
			tag_category_map[tag_in_user_language] = obj['category']
		return item_obj, tags, category_tag_map, tag_category_map

	def set_item_clearence(self, item_id, clearence, user = '', session = None) :
		self.update_item_query(item_id, {'$set': {'clearence': int(clearence)}}, session = session)

	def add_item(self, tags, item, clearence, fields_to_index = [], user = '', session = None, id_override = '') :
		tag_ids = self.filter_and_translate_tags(tags)
		field_texts = [item[field] for field in fields_to_index]
		word_ids = build_index(field_texts, session = session)
		if id_override :
			item_id = self.db[self.db_name].insert_one({
				'_id': id_override,
				'clearence': int(clearence),
				'tags': tag_ids + word_ids,
				'item': item,
				'tag_count': int(len(tag_ids)),
				'meta': {
					'created_by': user,
					'created_at': datetime.now(),
					'modified_by': user,
					'modified_at': datetime.now()
				}
			}, session = session).inserted_id
		else :
			item_id = self.db[self.db_name].insert_one({
				'clearence': int(clearence),
				'tags': tag_ids + word_ids,
				'item': item,
				'tag_count': int(len(tag_ids)),
				'meta': {
					'created_by': user,
					'created_at': datetime.now(),
					'modified_by': user,
					'modified_at': datetime.now()
				}
			}, session = session).inserted_id
		self.db.tags.update_many({'id': {'$in': tag_ids}}, {'$inc': {'count': int(1)}}, session = session)
		if self.db_name == 'videos' :
			self.db.tag_history.insert_one({
				'vid': ObjectId(item_id),
				'user': user,
				'tags': [],
				'add': tag_ids,
				'del': [],
				'time': datetime.now()
			}, session = session)
		self.aci.SetCountDiff([(tagid, 1) for tagid in tag_ids])
		return item_id

	def remove_item(self, item_id_or_item_object, user = '', session = None) :
		if isinstance(item_id_or_item_object, ObjectId) or isinstance(item_id_or_item_object, str):
			item = self.db[self.db_name].find_one({'_id': ObjectId(item_id_or_item_object)}, session = session)
			if item is None:
				raise UserError('ITEM_NOT_EXIST')
		else:
			item = item_id_or_item_object
		tag_ids = list(filter(lambda x: x < 0x80000000, item['tags']))
		word_ids = list(filter(lambda x: x >= 0x80000000, item['tags']))
		remove_index(word_ids, session = session)
		self.db.tags.update_many({'id': {'$in': tag_ids}}, {'$inc': {'count': int(-1)}}, session = session)
		if self.db_name == 'videos' :
			self.db.tag_history.insert_one({
				'vid': item['_id'],
				'user': user,
				'tags': [],
				'add': [],
				'del': tag_ids,
				'time': datetime.now()
			}, session = session)
		self.db[self.db_name].delete_one({'_id': item['_id']}, session = session)
		self.aci.SetCountDiff([(tagid, -1) for tagid in tag_ids])

	def filter_tags(self, tags, session = None) :
		found_tags = self.db.tag_alias.find({'tag': {'$in': tags}}, session = session)
		tm = [tag['tag'] for tag in found_tags]
		return tm

	def update_item(self, item_id, item, user = '', session = None):
		item = self.db[self.db_name].find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None:
			raise UserError('ITEM_NOT_EXIST')
		self.db[self.db_name].update_one({'_id': ObjectId(item_id)}, {'$set': {'item': item, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

	def update_item_query(self, item_id_or_item_object, query, fields_to_index = [], user = '', session = None):
		"""
		Your update query MUST NOT modify tags
		"""
		if isinstance(item_id_or_item_object, ObjectId) or isinstance(item_id_or_item_object, str):
			item = self.db[self.db_name].find_one({'_id': ObjectId(item_id_or_item_object)}, session = session)
			if item is None:
				raise UserError('ITEM_NOT_EXIST')
		else:
			item = item_id_or_item_object
		# if fields_to_index and '$set' in query and 'item' in query['$set'] :
		# 	all_reindex = True
		# 	for field in fields_to_index :
		# 		if field not in query['$set']['item'] :
		# 			all_reindex = False
		# 			break
		# 	if all_reindex :
		# 		field_texts = [query['$set']['item'][field] for field in fields_to_index]
		# 		tag_ids = list(filter(lambda x: x < 0x80000000, item['tags']))
		# 		word_ids = list(filter(lambda x: x >= 0x80000000, item['tags']))
		# 		remove_index(word_ids, session = session)
		# 		new_word_ids = build_index(field_texts, session = session)
		# 		self.db[self.db_name].update_one({'_id': ObjectId(item['_id'])}, {'$set': {'tags': tag_ids + new_word_ids}}, session = session)
		if fields_to_index and '$set' in query :
			field_texts = []
			if 'item' in query['$set'] :
				for field in fields_to_index :
					if field in query['$set']['item'] :
						field_texts.append(query['$set']['item'][field])
			for field in fields_to_index :
				if field in query['$set'] :
					field_texts.append(query['$set'][field])
			tag_ids = list(filter(lambda x: x < 0x80000000, item['tags']))
			word_ids = list(filter(lambda x: x >= 0x80000000, item['tags']))
			remove_index(word_ids, session = session)
			new_word_ids = build_index(field_texts, session = session)
			self.db[self.db_name].update_one({'_id': ObjectId(item['_id'])}, {'$set': {'tags': tag_ids + new_word_ids}}, session = session)
				
		if query :
			self.db[self.db_name].update_one({'_id': ObjectId(item['_id'])}, query, session = session)
		if user :
			self.db[self.db_name].update_one({'_id': ObjectId(item['_id'])}, {'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

	def _log_tag_update(self, user, vid : ObjectId, old_tags, new_tags, session = None) :
		added, removed = _diff(old_tags, new_tags)
		if added or removed :
			if self.db_name == 'videos' :
				self.db.tag_history.insert_one({
					'vid': vid,
					'user': user,
					'tags': old_tags,
					'add': added,
					'del': removed,
					'time': datetime.now()
				}, session = session)

	def update_item_tags(self, item_id_or_item_object, new_tags, user: ObjectId = '', session = None):
		new_tag_ids = self.filter_and_translate_tags(new_tags)
		if isinstance(item_id_or_item_object, ObjectId) or isinstance(item_id_or_item_object, str):
			item = self.db[self.db_name].find_one({'_id': ObjectId(item_id_or_item_object)}, session = session)
			if item is None:
				raise UserError('ITEM_NOT_EXIST')
		else:
			item = item_id_or_item_object
		index_tags = list(filter(lambda x: x >= 0x80000000, item['tags']))
		real_tags = list(filter(lambda x: x < 0x80000000, item['tags']))
		new_tag_ids = self._trigger_tag_rule_and_action(user, item_id_or_item_object['_id'], real_tags, new_tag_ids, session = session)
		self._log_tag_update(user, item_id_or_item_object['_id'], real_tags, new_tag_ids, session = session)
		self.db.tags.update_many({'id': {'$in': real_tags}}, {'$inc': {'count': -1}}, session = session)
		self.db.tags.update_many({'id': {'$in': new_tag_ids}}, {'$inc': {'count': 1}}, session = session)
		self.db[self.db_name].update_one({'_id': ObjectId(item['_id'])}, {'$set': {'tags': new_tag_ids + index_tags, 'tag_count': int(len(new_tag_ids)), 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		self.aci.SetCountDiff([(t, -1) for t in item['tags']])
		self.aci.SetCountDiff([(t, 1) for t in new_tag_ids])

	def _get_many_tag_counts(self, item_ids = None, tags = None, user = '', session = None):
		id_match_obj = { '_id' : { '$in': item_ids } } if item_ids else {}
		tag_match_obj = { '_id' : { '$in' : tags } } if tags else {}
		return self.db[self.db_name].aggregate([
		{
			"$match" : id_match_obj
		},
		{
			"$project" : {'tags': {'$filter': {'input': '$tags', 'as': 'tag', 'cond': {'$lt': ['$$tag', 0x80000000]}}}}
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
		if not new_tags or not item_ids :
			return
		if isinstance(new_tags[0], int) :
			new_tag_ids = new_tags
		else :
			new_tag_ids = self.filter_and_translate_tags(new_tags)
		prior_tag_counts = dict([(item['_id'], item['count']) for item in self._get_many_tag_counts(item_ids, new_tag_ids, user, session)])
		# TODO: trigger tag rule and action
		history_items = list(self.db[self.db_name].aggregate([
			{'$match': {'_id': {'$in': item_ids}}},
			{'$project': {'vid': '$_id', 'tags': {'$filter': {'input': '$tags', 'as': 'tag', 'cond': {'$lt': ['$$tag', 0x80000000]}}}}},
			{'$project': {'vid': 1, 'tags': 1, 'add': {'$setDifference': [new_tag_ids, '$tags']}}},
			{'$addFields': {'del': [], 'time': datetime.now(), 'user': user}},
			{'$match': {'$or': [{'del': {'$not': {'$size': 0}}}, {'add': {'$not': {'$size': 0}}}]}}
		], session = session))
		if history_items :
			for i in history_items :
				del i['_id']
			if self.db_name == 'videos' :
				self.db.tag_history.insert_many(history_items, session = session)
		self.db[self.db_name].update_many({'_id': {'$in': item_ids}}, {
			'$addToSet': {'tags': {'$each': new_tag_ids}},
			'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		num_items = len(item_ids)
		new_tag_count_diff = [(tag, num_items - prior_tag_counts.get(tag, 0)) for tag in new_tag_ids]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'id': tag}, {'$inc': {'count': diff}}, session = session) # $inc is atomic, no locking needed
		item_objs = self.db[self.db_name].aggregate([
			{'$match': {'_id': {'$in': item_ids}}},
			{'$project': {'vid': '$_id', 'tags': {'$filter': {'input': '$tags', 'as': 'tag', 'cond': {'$lt': ['$$tag', 0x80000000]}}}}},
		], session = session)
		for obj in item_objs :
			self.db[self.db_name].update_one({'_id': obj['vid']}, {'$set': {'tag_count': int(len(obj['tags']))}}, session = session)
		self.aci.SetCountDiff(new_tag_count_diff)

	def update_many_items_tags_pull(self, item_ids, tags_to_remove, user = '', session = None):
		if not tags_to_remove or not item_ids :
			return
		if isinstance(tags_to_remove[0], int) :
			tag_ids_to_remove = tags_to_remove
		else :
			tag_ids_to_remove = self.filter_and_translate_tags(tags_to_remove)
		prior_tag_counts = dict([(item['_id'], item['count']) for item in self._get_many_tag_counts(item_ids, tag_ids_to_remove, user, session)])
		# TODO: trigger tag rule and action
		history_items = list(self.db[self.db_name].aggregate([
			{'$match': {'_id': {'$in': item_ids}}},
			{'$project': {'vid': '$_id', 'tags': {'$filter': {'input': '$tags', 'as': 'tag', 'cond': {'$lt': ['$$tag', 0x80000000]}}}}},
			{'$project': {'vid': 1, 'tags': 1, 'del': {'$setIntersection': [tag_ids_to_remove, '$tags']}}},
			{'$addFields': {'add': [], 'time': datetime.now(), 'user': user}},
			{'$match': {'$or': [{'del': {'$not': {'$size': 0}}}, {'add': {'$not': {'$size': 0}}}]}}
		], session = session))
		if history_items :
			for i in history_items :
				del i['_id']
			if self.db_name == 'videos' :
				self.db.tag_history.insert_many(history_items, session = session)
		self.db[self.db_name].update_many({'_id': {'$in': item_ids}}, {
			'$pullAll': {'tags': tag_ids_to_remove},
			'$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		new_tag_count_diff = [(tag, -prior_tag_counts.get(tag, 0)) for tag in tag_ids_to_remove]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'id': tag}, {'$inc': {'count': diff}}, session = session)
			item_objs = self.db[self.db_name].aggregate([
			{'$match': {'_id': {'$in': item_ids}}},
			{'$project': {'vid': '$_id', 'tags': {'$filter': {'input': '$tags', 'as': 'tag', 'cond': {'$lt': ['$$tag', 0x80000000]}}}}},
		], session = session)
		for obj in item_objs :
			self.db[self.db_name].update_one({'_id': obj['vid']}, {'$set': {'tag_count': int(len(obj['tags']))}}, session = session)
		self.aci.SetCountDiff(new_tag_count_diff)

	def update_item_tags_merge(self, item_id, new_tags, user = '', session = None, remove_tagids = []):
		if not new_tags :
			return
		if isinstance(new_tags[0], int) :
			new_tag_ids = new_tags
		else :
			new_tag_ids = self.filter_and_translate_tags(new_tags)
		item = self.db[self.db_name].find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None :
			raise UserError('ITEM_NOT_EXIST')
		old_tag_ids = list(filter(lambda x: x < 0x80000000, item['tags']))
		new_tag_ids = set(new_tag_ids)
		remove_tagids = set(remove_tagids)
		remove_tagids = remove_tagids - new_tag_ids
		merged_tag_ids = list((set(old_tag_ids) | new_tag_ids) - remove_tagids)
		merged_tag_ids = self._trigger_tag_rule_and_action(user, item['_id'], old_tag_ids, merged_tag_ids, session = session)
		self._log_tag_update(user, item['_id'], old_tag_ids, merged_tag_ids, session = session)
		self.db[self.db_name].update_one({'_id': ObjectId(item_id)}, {
			'$addToSet': {'tags': {'$each': merged_tag_ids}},
			'$set': {'tag_count': int(len(merged_tag_ids)), 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		tags_added, _ = _diff(old_tag_ids, merged_tag_ids)
		new_tag_count_diff = [(tagid, 1) for tagid in tags_added]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'id': tag}, {'$inc': {'count': diff}}, session = session)
		self.aci.SetCountDiff(new_tag_count_diff)

	def update_item_tags_pull(self, item_id, tags_to_remove, user = '', session = None):
		if not tags_to_remove :
			return
		if isinstance(tags_to_remove[0], int) :
			tag_ids_to_remove = tags_to_remove
		else :
			tag_ids_to_remove = self.filter_and_translate_tags(tags_to_remove)
		item = self.db[self.db_name].find_one({'_id': ObjectId(item_id)}, session = session)
		if item is None :
			raise UserError('ITEM_NOT_EXIST')
		old_tag_ids = list(filter(lambda x: x < 0x80000000, item['tags']))
		merged_tag_ids = list(set(old_tag_ids) - set(tags_to_remove))
		merged_tag_ids = self._trigger_tag_rule_and_action(user, item['_id'], old_tag_ids, merged_tag_ids, session = session)
		self._log_tag_update(user, item['_id'], old_tag_ids, merged_tag_ids, session = session)
		self.db[self.db_name].update_one({'_id': ObjectId(item_id)}, {
			'$pullAll': {'tags': tag_ids_to_remove},
			'$set': {'tag_count': int(len(merged_tag_ids)), 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
		_, tags_removed = _diff(old_tag_ids, merged_tag_ids)
		new_tag_count_diff = [(tagid, -1) for tagid in tags_removed]
		for (tag, diff) in new_tag_count_diff:
			self.db.tags.update_one({'id': tag}, {'$inc': {'count': diff}}, session = session)
		self.aci.SetCountDiff(new_tag_count_diff)

	def remove_alias(self, alias_name, user = '', session = None) :
		tag_obj = self._tag(alias_name, session = session)
		rc, lang_referenced = self._get_tag_name_reference_count(alias_name, tag_obj)
		if rc == 1 and lang_referenced is None :
			self.db.tags.update_one({'_id': tag_obj['_id']}, {'$pullAll': {'alias': [alias_name]}}, session = session)
			self.db.tag_alias.delete_one({'tag': alias_name}, session = session)
			self.aci.DeleteWord(alias_name)
		else :
			raise UserError('NOT_ALIAS')

	def add_tag_group(self, group_name, tags = [], user = '', session = None):
		g_obj = self.db.groups.find_one({'name': group_name}, session = session)
		if g_obj is not None:
			raise UserError('GROUP_EXIST')
		self.db.groups.insert_one({
			'name': group_name,
			'tags': tags,
			'meta': {
				'created_by': user,
				'created_at': datetime.now(),
				'modified_by': user,
				'modified_at': datetime.now()
			}
		}, session = session)

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
		ret = self.db.tag_alias.aggregate([
			{'$match': {'tag' : {'$regex' : query}}},
			{'$lookup': {"from" : "tags", "localField" : "dst", "foreignField" : "_id", "as" : "tag_obj"}},
			{'$unwind': {'path': '$tag_obj'}},
			{'$project': {'tag_obj.id': 1}}
		])
		return [item['tag_obj']['id'] for item in ret]

	def compile_query(self, query : str, query_type = 'tag', session = None):
		query = query.strip()
		if not query :
			return {}, []
		if query_type == 'text' :
			query_obj, tags = Parser.parse(query, self.translate_text, self.translate_tag_group, self.translate_tag_wildcard)
		else :
			query_obj, tags = Parser.parse(query, self.translate_tags, self.translate_tag_group, self.translate_tag_wildcard)
		if query_obj is None:
			raise UserError('INCORRECT_QUERY')
		return query_obj, tags

	def _tag(self, tag, return_none = False, session = None) :
		if isinstance(tag, int) :
			ans = self.db.tags.find_one({'id': tag}, session = session)
			if ans is None :
				raise UserError('TAG_NOT_EXIST')
			return ans
		elif isinstance(tag, dict) :
			return tag
		elif isinstance(tag, str) :
			alias_obj = self.db.tag_alias.find_one({'tag': re.compile('^' + re.escape(tag) + '$', re.IGNORECASE)}, session = session)
			if alias_obj is None :
				if return_none :
					return None
				raise UserError('TAG_NOT_EXIST')
			ans = self.db.tags.find_one({'_id': alias_obj['dst']}, session = session)
			assert ans is not None
			return ans
		elif isinstance(tag, ObjectId) :
			ans = self.db.tags.find_one({'_id': tag}, session = session)
			if ans is None :
				if return_none :
					return None
				raise UserError('TAG_NOT_EXIST')
			return ans
		else :
			assert False, 'UNKNOWN_TAG_TYPE'

	def get_tag_object(self, tag, return_none = False, session = None) :
		return self._tag(tag, return_none, session)

	def _check_language(self, language):
		if language not in VALID_LANGUAGES :
			raise UserError('UNRECOGNIZED_LANGUAGE')

	def _check_category(self, category, session) :
		cat = self.db.cats.find_one({'name': category}, session = session)
		if cat is None:
			raise UserError('CATEGORY_NOT_EXIST')
		return cat

	def _trigger_tag_rule_and_action(self, user, vid : ObjectId, old_tags, new_tags, session = None) :
		return new_tags

	def add_tag_rule(self, match_query_str, tags_to_add = [], tags_to_remove = [], session = None) :
		pass # return rule id

	def update_tag_rule(self, rule_id, match_query_str, tags_to_add = [], tags_to_remove = [], session = None) :
		pass

	def remove_tag_rule(self, rule_id, session = None) :
		pass

	def add_tag_action(self, match_query_str, action_func, invalid_action = None, action_data = None, session = None) :
		# action_func(item_id, loads(action_data_json_str))
		pass # return action id

	def update_tag_action(self, action_id, match_query_str, action_func = None, action_data = None, session = None) :
		pass

	def remove_tag_action(self, action_id, session = None) :
		pass

	
	def mine_pattern_FPTree(self) :
		pass
