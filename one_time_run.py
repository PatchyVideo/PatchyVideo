

from db import db, client, tagdb
from utils.dbtools import MongoTransaction
from bson import ObjectId
'''
if __name__ == '__main__' :
    with MongoTransaction(client) as s :
        for item in [i for i in db.items.find({'item.cover_image':'','item.site':'youtube'},session=s())]:
            print('Updating %s'%item['item']['unique_id'])
            yid = item['item']['unique_id'].split(':')[1]
            data = {
                'title':item['item']['title'],
                'desc':item['item']['desc'],
                'site':item['item']['site'],
                'unique_id':item['item']['unique_id'],
                'thumbnailURL':"https://img.youtube.com/vi/%s/hqdefault.jpg"%yid,
                }
            new_data = _make_video_data(data,item['item']['copies'],item['item']['series'],item['item']['url'])
            db.items.update_one({'_id':ObjectId(item['_id'])},{'$set':{
                'item.cover_image':new_data['cover_image'],
                'item.thumbnail_url':new_data['thumbnail_url']}},session=s())
                
            print('New image:%s'%new_data['cover_image'])
        s.mark_succeed()

'''

"""
if __name__ == '__main__' :
    with MongoTransaction(client) as s :
        all_tags = [t for t in db.tags.find(session = s())]
        all_root_tags = [t for t in db.tags.find({'dst': {'$exists': False}}, session = s()).sort([("meta.created_at", 1)])]
        all_alias_tags = [t for t in db.tags.find({'dst': {'$exists': True}}, session = s())]
        db.tags.delete_many({}, session = s())
        db.cats.update_many({}, {'$set': {'count': 0}}, session = s())
        tag_map = {}
        for rt in all_root_tags :
            tag_id = tagdb.add_tag(rt['tag'], rt['category'], rt['language'], session = s())
            tag_map[rt['tag']] = tag_id
            db.tags.update_one({'id': tag_id}, {'$set': {'count': int(rt['count'])}}, session = s())
            print(f"{rt['language']}: {rt['tag']} -> {tag_id}")
        for tt in all_alias_tags :
            if tt['type'] == 'language' :
                tagdb.add_or_rename_tag(tt['dst'], tt['tag'], tt['language'], session = s())
                print(f"{tt['language']}: {tt['tag']} -> {tt['dst']}")
        video_tag_map = {}
        for vid in db.items.find(session = s()) :
            tag_ids = []
            for t in vid['tags'] :
                if t not in tag_map :
                    print(f"!!! tag {t} does not exist for video {vid['_id']} {vid['item']['title']}")
                else :
                    tag_ids.append(tag_map[t])
            video_tag_map[str(vid['_id'])] = tag_ids
            #print(f"{vid['tags']} -> {tag_ids}")
        for (_id, tags) in video_tag_map.items() :
            db.items.update_one({'_id': ObjectId(_id)}, {'$set': {'tags': tags}}, session = s())
        s.mark_succeed()
"""

if __name__ == '__main__' :
    from db.index.index_builder import build_index
    #with MongoTransaction(client) as s :
    db.items.update_many({}, {'$pull': {'tags': {'$gte': 0x80000000}}}, session = s())
    db.index_words.delete_many({}, session = s())
    #    s.mark_succeed()
    cursor = db.items.find(no_cursor_timeout = True).batch_size(100)
    #with MongoTransaction(client) as s :
    for item in cursor :
        print(item['item']['title'])
        word_ids = build_index([item['item']['desc'], item['item']['title']], session = s())
        db.items.update_one({'_id': item['_id']}, {'$set': {'tags': item['tags'] + word_ids}})
    #    s.mark_succeed()
