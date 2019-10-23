from datetime import datetime

if __name__ == '__main__':
    from flask_pymongo import PyMongo
    from flask import Flask
    from query_parser import Parser
    from bson import ObjectId
    from collections import defaultdict
    
else:
    from .query_parser import Parser

    from bson import ObjectId
    from collections import defaultdict
    

def _diff(old_tags, new_tags):
    old_tags_set = set(old_tags)
    new_tags_set = set(new_tags)
    added_tags = new_tags_set - old_tags_set
    removed_tags = (new_tags_set ^ old_tags_set) - added_tags
    return list(added_tags), list(removed_tags)

class TagDB():
    def __init__(self, db):
        self.db = db

    def add_category(self, category, user = '', session = None):
        cat = self.db.cats.find_one({'name': category}, session = session)
        if cat is not None:
            return 'CATEGORY_EXIST'
        self.db.cats.insert_one({'name': category, 'count': 0, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session)
        return 'SUCCESS'

    def list_categories(self, session = None):
        ans = []
        for item in self.db.cats.find({}, session = session):
            ans.append(item)
        return ans
    
    def list_category_tags(self, category, session = None):
        cat = self.db.cats.find_one({'name': category}, session = session)
        if cat is None:
            return 'CATEGORY_NOT_EXIST'
        ans = self.db.tags.find({'category': category}, session = session)
        return ans

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
        return 'SUCCESS'

    def add_tag(self, tag, category, user = '', session = None):
        cat = self.db.cats.find_one({'name': category}, session = session)
        if cat is None:
            return 'CATEGORY_NOT_EXIST'
        tag_obj = self.db.tags.find_one({'tag': tag}, session = session)
        if tag_obj is not None:
            return 'TAG_EXIST'
        self.db.tags.insert_one({'category': category, 'tag': tag, 'meta': {'created_by': user, 'created_at': datetime.now()}, 'count': 0}, session = session)
        self.db.cats.update_one({'name': category}, {'$inc': {'count': 1}}, session = session)
        return 'SUCCESS'

    def filter_tags(self, tags, session = None):
        found = self.db.tags.aggregate([
            {'$match':{'tag':{'$in':tags}}},
            {'$project':{'tag':1}}], session = session)
        return [item['tag'] for item in found]

    def remove_tag(self, tag, user = '', session = None):
        tt, tag_obj = self._tag_type(tag, session = session)
        if tt == 'tag':   
            self.db.tags.delete_one({'_id': tag_obj['_id']}, session = session)
            self.db.cats.update_one({'name': tag_obj['category']}, {'$inc': {'count': -1}}, session = session)
            self.db.items.update_many({'tags': tag}, {'$pull': {'tags': tag}}, session = session)
            return 'SUCCESS'
        elif tt == 'alias':
            self.db.alias.delete_one({'_id': tag_obj['_id']}, session = session)
        else:
            return 'TAG_NOT_EXIST'

    def rename_tag(self, tag, new_tag, user = None, session = None):
        tt, tag_obj = self._tag_type(tag, session = session)
        if tt == 'tag':
            tag_obj2 = self.db.tags.find_one({'tag': new_tag}, session = session)
            if tag_obj2 is not None:
                return 'TAG_EXIST'
            self.db.tags.update_one({'_id': tag_obj['_id']}, {'$set': {'tag': new_tag, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
            self.db.items.update_many({'tags': {'$elemMatch': {'$eq': tag}}}, {'$set': {'tags.$': new_tag}}, session = session)
            return 'SUCCESS'
        elif tt == 'alias':
            self.db.alias.update_one({'_id': tag_obj['_id']}, {'$set': {'src': new_tag}}, session = session)
        else:
            return 'TAG_NOT_EXIST'

    def retrive_items(self, tag_query, session = None):
        return self.db.items.find(tag_query, session = session)

    def retrive_item(self, tag_query, session = None):
        return self.db.items.find_one(tag_query, session = session)

    def retrive_tags(self, item_id, session = None):
        item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
        if item is None:
            return 'ITEM_NOT_EXIST' 
        return item['tags']
    
    def retrive_item_tags_with_category(self, item_id, session = None):
        item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
        if item is None:
            return 'ITEM_NOT_EXIST'
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
        return item_id

    def verify_tags(self, tags, session = None):
        tags = self.translate_tags(tags, session = session)
        found_tags = self.db.tags.find({'tag': {'$in': tags}}, session = session)
        tm = []
        for tag in found_tags:
            tm.append(tag['tag'])
        for tag in tags:
            if not tag in tm:
                return 'TAG_NOT_EXIST', tag
        return 'SUCCESS', None

    def update_item(self, item_id, item, user = '', session = None):
        item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
        if item is None:
            return 'ITEM_NOT_EXIST'
        self.db.items.update_one({'_id': ObjectId(item_id)}, {'$set': {'item': item, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
        return 'SUCCESS'

    def update_item_query(self, item_id, query, session = None):
        item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
        if item is None:
            return 'ITEM_NOT_EXIST'
        self.db.items.update_one({'_id': ObjectId(item_id)}, query, session = session)
        return 'SUCCESS'

    def update_item_tags(self, item_id, new_tags, user = '', session = None):
        item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
        if item is None:
            return 'ITEM_NOT_EXIST'
        self.db.tags.update_many({'tag': {'$in': item['tags']}}, {'$inc': {'count': -1}}, session = session)
        self.db.tags.update_many({'tag': {'$in': new_tags}}, {'$inc': {'count': 1}}, session = session)
        self.db.items.update_one({'_id': ObjectId(item_id)}, {'$set': {'tags': new_tags, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
        return 'SUCCESS'

    def update_many_items_tags_merge(self, item_ids, new_tags, user = '', session = None):
        return self.db.items.update_many({'_id': {'$in': item_ids}}, {
            '$addToSet': {'tags': {'$each': new_tags}},
            '$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

    def update_many_items_tags_pull(self, item_ids, tags_to_remove, user = '', session = None):
        return self.db.items.update_many({'_id': {'$in': item_ids}}, {
            '$pullAll': {'tags': tags_to_remove},
            '$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

    def update_item_tags_merge(self, item_id, new_tags, user = '', session = None):
        item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
        if item is None :
            return 'ITEM_NOT_EXIST'
        return self.db.items.update_one({'_id': ObjectId(item_id)},  {
            '$addToSet': {'tags': {'$each': new_tags}},
            '$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

    def update_item_tags_pull(self, item_id, tags_to_remove, user = '', session = None):
        item = self.db.items.find_one({'_id': ObjectId(item_id)}, session = session)
        if item is None :
            return 'ITEM_NOT_EXIST'
        return self.db.items.update_one({'_id': ObjectId(item_id)},  {
            '$pullAll': {'tags': tags_to_remove},
            '$set': {'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)

    def add_tag_alias(self, src_tag, dst_tag, user = '', session = None):
        tt_dst, tag_obj_dst = self._tag_type(dst_tag, session = session)
        tt_src, tag_obj_src = self._tag_type(src_tag, session = session)
        if tt_dst == 'tag':
            if tt_src == 'tag':
                alias_obj = self.db.alias.find_one({'src': src_tag, 'dst': dst_tag}, session = session)
                if alias_obj is not None:
                    return 'ALIAS_EXIST'
                self.db.alias.insert_one({'src': src_tag, 'dst': dst_tag, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session)
                self.db.alias.update_many({'dst': src_tag}, {'dst': dst_tag, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session)
                self.db.items.update_many({'tags': {'$elemMatch': {'$eq': src_tag}}}, {'$set': {'tags.$': dst_tag, 'meta': {'created_by': user, 'created_at': datetime.now()}}}, session = session)
                src_post_count = tag_obj_src['count']
                self.db.tags.update_one({'_id': ObjectId(tag_obj_src)}, {'$set': {'count': 0}}, session = session)
                self.db.tags.update_one({'_id': ObjectId(tag_obj_dst)}, {'$inc': {'count': src_post_count}}, session = session)
                return 'SUCCESS'
            elif tt_src == 'alias':
                # override an existing alias
                self.db.alias.update_one({'src': src_tag}, {'$set': {'dst': dst_tag, 'meta': {'created_by': user, 'created_at': datetime.now()}}}, session = session)
                return 'SUCCESS'
            else:
                return 'TAG_NOT_EXIST'
        elif tt_dst == 'alias':
            return self.add_tag_alias(src_tag, tag_obj_dst['dst'], user, session = session)
        else:
            return 'TAG_NOT_EXIST'

    def remove_tag_alias(self, src_tag, user = '', session = None):
        tt, tag_obj = self._tag_type(src_tag, session = session)
        if tt == 'tag':
            return 'NOT_ALIAS'
        elif tt == 'alias':
            self.db.alias.delete_many({'src': src_tag}, session = session)
        else:
            return 'ALIAS_NOT_EXIST'

    def translate_tags(self, tags, session = None):
        src_tag_objs = self.db.alias.find({'src': {'$in': tags}}, session = session)
        tag_map = {}
        for item in src_tag_objs:
            tag_map[item['src']] = item['dst']
        return [tag_map[tag] if tag in tag_map else tag for tag in tags]

    def count_items(self, tag_query, session = None):
        pass

    def count_items_tag(self, tag, session = None):
        pass

    def add_tag_group(self, group_name, tags = [], user = '', session = None):
        g_obj = self.db.groups.find_one({'name': group_name}, session = session)
        if g_obj is not None:
            return 'GROUP_EXIST'
        self.db.groups.insert_one({'name': group_name, 'tags': tags, 'meta': {'created_by': user, 'created_at': datetime.now()}}, session = session)
        return 'SUCCESS'

    def remove_tag_group(self, group_name, user = '', session = None):
        g_obj = self.db.groups.find_one({'name': group_name}, session = session)
        if g_obj is None:
            return 'GROUP_NOT_EXIST'
        self.db.groups.remove({'name': group_name}, session = session)
        return 'SUCCESS'

    def list_tag_group(self, group_name, session = None):
        g_obj = self.db.groups.find_one({'name': group_name}, session = session)
        if g_obj is None:
            return 'GROUP_NOT_EXIST'
        return g_obj['tags']

    def update_tag_group(self, group_name, new_tags, user = '', session = None):
        g_obj = self.db.groups.find_one({'name': group_name}, session = session)
        if g_obj is None:
            return 'GROUP_NOT_EXIST'
        self.db.groups.update_one({'name': group_name}, {'$set': {'tags': new_tags, 'meta.modified_by': user, 'meta.modified_at': datetime.now()}}, session = session)
        return 'SUCCESS'

    def translate_tag_group(self, groups, session = None):
        gm = {}
        g_objs = self.db.groups.find({'name': {'$in': groups}}, session = session)
        for g_obj in g_objs:
            gm[g_obj['name']] = g_obj['tags']
        for g in groups:
            if not g in gm:
                gm[g] = []
        return gm

    def compile_query(self, query, session = None):
        query_obj, tags = Parser.parse(query, self.translate_tags, self.translate_tag_group)
        if query_obj is None:
            return 'INCORRECT_QUERY', []
        return query_obj, tags

    def _tag_type(self, tag, session = None):
        if not isinstance(tag, str) :
            return 'tag', tag
        tag_obj = self.db.tags.find_one({'tag': tag}, session = session)
        if tag_obj is None:
            return None, None
        alias_obj = self.db.alias.find_one({'src': tag}, session = session)
        if alias_obj is None:
            return 'tag', tag_obj
        else:
            return 'alias', alias_obj

    def _check_tag_name(self, tag, session = None):
        return True


if __name__ == '__main__':
    app = Flask('WebVideoIndexing')
    app.config["MONGO_URI"] = "mongodb://localhost:27017/patchyvideo"
    mongo = PyMongo(app)
    db = TagDB(mongo.db.patchyvideo)
    db.add_category('General')
    db.add_category('Character')
    db.add_category('Copyright')
    db.add_category('Author')
    db.add_category('Meta')
    db.add_category('Language')
