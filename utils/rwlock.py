
import os
import redis

from redisrwlock import Rwlock, RwlockClient

_rw_rdb = redis.StrictRedis(host = os.getenv('REDISTOGO_URL', 'redis'))
_client = RwlockClient(redis = _rw_rdb)

class WriterLock() :
    def __init__(self, name) :
        self.name = name
        
    def __enter__(self) :
        self.lock = _client.lock(self.name, Rwlock.WRITE, timeout = Rwlock.FOREVER)
        if self.lock.status == Rwlock.OK:
            return self
        elif self.lock.status == Rwlock.DEADLOCK:
            raise Exception('Deadlock in redis WriterLock')

    def __exit__(self, type, value, traceback) :
        _client.unlock(self.lock)

class ReaderLock() :
    def __init__(self, name) :
        self.name = name
        
    def __enter__(self) :
        self.lock = _client.lock(self.name, Rwlock.READ, timeout = Rwlock.FOREVER)
        if self.lock.status == Rwlock.OK:
            return self
        elif self.lock.status == Rwlock.DEADLOCK:
            raise Exception('Deadlock in redis ReaderLock')

    def __exit__(self, type, value, traceback) :
        _client.unlock(self.lock)
