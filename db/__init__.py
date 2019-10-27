
from init import app
import os

from pymongo import MongoClient
# repilcate set is only used in production
if os.getenv("FLASK_ENV", "development") == "production" :
    client = MongoClient(os.getenv('MONGODB_URL', "mongodb://db:27017/"), replicaSet = 'rs1')
else :
    client = MongoClient(os.getenv('MONGODB_URL', "mongodb://localhost:27017/"))
db = client['patchyvideo']

from .TagDB import TagDB
tagdb = TagDB(db)

# add initial tag categories
tagdb.add_category('General')
tagdb.add_category('Character')
tagdb.add_category('Copyright')
tagdb.add_category('Author')
tagdb.add_category('Meta')
tagdb.add_category('Language')
