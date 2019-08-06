
from init import app
import os

#from flask_pymongo import PyMongo
#app.config["MONGO_URI"] = os.getenv('MONGODB_URL', "mongodb://db:27017/patchyvideo")
from pymongo import MongoClient
client = MongoClient(os.getenv('MONGODB_URL', "mongodb://db:27017/"), replicaSet = 'rs1')
#db = PyMongo(app).db.patchyvideo
db = client['patchyvideo']

from .TagDB import TagDB
tagdb = TagDB(db)
tagdb.add_category('General')
tagdb.add_category('Character')
tagdb.add_category('Copyright')
tagdb.add_category('Author')
tagdb.add_category('Meta')
tagdb.add_category('Language')
