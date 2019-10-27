
from datetime import datetime
from bson import ObjectId

def makeUserMeta(user):
    if user is None :
        return ''
    else :
        return user['_id']

def makeUserMetaObject(user):
    if user is None :
        return {'created_by': '', 'created_at': datetime.now()}
    else :
        return {'created_by': ObjectId(user['_id']), 'created_at': datetime.now()}

class MongoTransactionEnabled(object) :
    def __init__(self, client) :
        self.client = client
        self.succeed = False

    def mark_succeed(self) :
        self.succeed = True

    def mark_failover(self) :
        self.succeed = False

    def __enter__(self) :
        self.session = self.client.start_session()
        self.session.__enter__()
        self.session.start_transaction()
        return self

    def __call__(self) :
        return self.session

    def __exit__(self, type, value, traceback) :
        if self.succeed :
            self.session.commit_transaction()
        self.session.__exit__(type, value, traceback)

class MongoTransactionDisabled(object) :
    def __init__(self, client) :
        pass

    def mark_succeed(self) :
        pass

    def mark_failover(self) :
        pass

    def __enter__(self) :
        return self

    def __call__(self) :
        return None

    def __exit__(self, type, value, traceback) :
        pass

import os
if os.getenv("ENABLE_TRANSACTION", "false") == 'true' :
    MongoTransaction = MongoTransactionEnabled
else :
    MongoTransaction = MongoTransactionDisabled
