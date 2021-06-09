
import os
import redis

from functools import wraps

from redisrwlock import Rwlock, RwlockClient

_rw_rdb = redis.StrictRedis(host = os.getenv('REDISTOGO_URL', 'redis'))
_client = RwlockClient(redis = _rw_rdb)

"""
Define reader-writer lock RAII helpers
"""

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

"""
Define reader-writer lock decorator helpers
"""

def modifyingResource(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            #with WriterLock(name) :
            return func(*args, **kwargs)
        return wrapper
    return decorator

def usingResource(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            #with ReaderLock(name) :
            return func(*args, **kwargs)
        return wrapper
    return decorator


