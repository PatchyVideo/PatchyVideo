
from services.postVideo import _make_video_data
from db import db, client
from utils.dbtools import MongoTransaction
from bson import ObjectId

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

