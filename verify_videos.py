
from db import tagdb
from services.playlist import listPlaylistsForVideoNoAuth

for item in tagdb.retrive_items({}).batch_size(100) :
    try :
        listPlaylistsForVideoNoAuth(item['_id'])
    except :
        print(item['_id'], item['item']['url'])

