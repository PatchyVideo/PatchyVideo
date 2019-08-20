
from db import db, tagdb, client as dbclient
from utils.dbtools import MongoTransaction
from utils.interceptors import jsonRequest, basePage
from flask import Flask, request
from collections import Counter
from bson import ObjectId

import atexit
import operator
import threading

app = Flask('PopularityTracker')
update_lock = threading.Lock()
hitmap_update_lock = threading.Lock()

class PopularityTracker(object) :
    def __init__(self, num_bins) :
        self.num_bins = num_bins
        self.idx = 0
        self.bins = [None] * (self.num_bins + 2)
        self.hitmap = {}
        self.hitmap_sorted = {}
        self._try_restore()

    def _try_restore(self, session = None) :
        try :
            item = db.popular_tags.find_one({}, session = session)
            self.hitmap = dict.fromkeys(item['hitmap'], 0)
            self.hitmap_sorted = self.hitmap
        except :
            pass

    def _try_save(self, session = None) :
        try :
            item = db.popular_tags.find_one({}, session = session)
            if item is not None :
                db.popular_tags.delete_one({'_id': ObjectId(item['_id'])})
            hitmap_update_lock.acquire()
            keys = list(self.hitmap_sorted.keys())
            hitmap_update_lock.release()
            db.popular_tags.insert_one({'hitmap': keys}, session = session)
        except :
            pass

    def update_current_bin(self, hitmap) :
        current_hitmap = self.bins[self.idx]
        if current_hitmap is not None :
            A = Counter(current_hitmap)
            B = Counter(hitmap)
            self.bins[self.idx] = dict(A + B)
        else :
            self.bins[self.idx] = hitmap

    def _sort(self) :
        hitmap_update_lock.acquire()
        self.hitmap_sorted = dict(sorted(self.hitmap.items(), key = operator.itemgetter(0), reverse = True))
        hitmap_update_lock.release()

    def update_popularity_and_move_to_next_bin(self) :
        next_bin_idx = (self.idx + 1) % (self.num_bins + 2)
        to_subtract_bin_idx = (self.idx + 2) % (self.num_bins + 2)
        all_hitmap = Counter(self.hitmap)
        current_bin = self.bins[self.idx]
        current_bin_tags = list(current_bin.keys())
        current_bin_tags = tagdb.filter_tags(current_bin_tags)
        current_bin = {tag: current_bin[tag] for tag in current_bin_tags}
        current_hitmap = Counter(current_bin)
        all_hitmap = all_hitmap + current_hitmap
        if self.bins[to_subtract_bin_idx] is not None :
            to_subtract_hitmap = Counter(self.bins[to_subtract_bin_idx])
            all_hitmap = all_hitmap - to_subtract_hitmap
        self.hitmap = all_hitmap
        self.idx = next_bin_idx
        self._sort()
        with MongoTransaction(dbclient) as s :
            self._try_save(s())
        return self.hitmap_sorted

tracker = PopularityTracker(7 * 24 * 6)

import json

@app.route("/hit", methods = ["POST"])
@basePage
@jsonRequest
def hit_page(rd, data) :
    #print('hit', data.hitmap)
    update_lock.acquire()
    try:
        tracker.update_current_bin(data.hitmap)
    except :
        pass
    update_lock.release()
    return "data", "your hit:" + json.dumps(data.hitmap)

@app.route("/get")
@basePage
def get_page(rd) :
    try :
        count = int(request.values['count'])
    except :
        count = 20
    hitmap_update_lock.acquire()
    count = min(count, len(tracker.hitmap_sorted))
    hitmap = list(tracker.hitmap_sorted.keys())[:count]
    hitmap_update_lock.release()
    return "json", {"tags": hitmap}

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(daemon = True)
# Explicitly kick off the background thread
scheduler.start()

def update_popularity() :
    tracker.update_popularity_and_move_to_next_bin()

atexit.register(lambda: scheduler.shutdown(wait = False))

if __name__ == "__main__":
    scheduler.add_job(update_popularity, 'interval', minutes = 10)
    #print('started')
    app.run(host = '0.0.0.0', port = 5001)

