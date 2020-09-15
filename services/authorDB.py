
from init import rdb
from db import db, tagdb, client
from utils.exceptions import UserError
from utils.dbtools import MongoTransaction
from config import AuthorDB
from services.tcb import filterOperation
from utils.logger import log
from utils.rwlock import usingResource, modifyingResource

from bson import ObjectId

import re

@modifyingResource('tags')
def createOrModifyAuthorRecord(user, author_type, tagid, common_tags, user_spaces, desc, avatar_file_key = None) :
    filterOperation('createOrModifyAuthorRecord', user)
    log(obj = {'author_type': author_type, 'tagid': tagid, 'common_tags': common_tags, 'user_spaces': user_spaces, 'desc': desc, 'avatar_file_key': avatar_file_key})
    if author_type not in ['individual', 'group'] :
        raise UserError('INCORRECT_AUTHOR_TYPE')
    if not isinstance(user_spaces, list) :
        raise UserError('INCORRECT_REQUEST_USER_SPACES')
    user_space_ids = createUserSpaceIds(user_spaces)
    if len(desc) > AuthorDB.DESC_MAX_LENGTH :
        raise UserError('DESC_TOO_LONG')
    with MongoTransaction(client) as s :
        tag_obj = tagdb._tag(tagid, session = s())
        if tag_obj['category'] != 'Author' :
            raise UserError('TAG_NOT_AUTHOR')
        existing_record = None
        log(obj = {'tag_obj': tag_obj})
        avatar_file = ''
        if 'author' in tag_obj :
            existing_record = db.authors.find_one({'_id': tag_obj['author']}, session = s())
            assert existing_record
            avatar_file = existing_record['avatar']
            log(obj = {'old_record': existing_record})
        common_tagids = tagdb.filter_and_translate_tags(common_tags, session = s())
        if avatar_file_key :
            if avatar_file_key.startswith("upload-image-") :
                filename = rdb.get(avatar_file_key)
                if filename :
                    avatar_file = filename.decode('ascii')
        if existing_record :
            record_id = existing_record['_id']
            db.authors.update_one({'_id': record_id}, {'$set': {
                'type': author_type,
                'tagid': tagid,
                'common_tagids': common_tagids,
                'urls': user_spaces,
                'user_space_ids': user_space_ids,
                'desc': desc,
                'avatar': avatar_file
            }}, session = s())
        else :
            record_id = db.authors.insert_one({
                'type': author_type,
                'tagid': tagid,
                'common_tagids': common_tagids,
                'urls': user_spaces,
                'user_space_ids': user_space_ids,
                'desc': desc,
                'avatar': avatar_file
            }, session = s()).inserted_id
            record_id = ObjectId(record_id)
        db.tags.update_one({'_id': tag_obj['_id']}, {'$set': {'author': record_id}})
        s.mark_succeed()
        return str(record_id)

BILIBILI_USER_SPACE = r"(https:\/\/|http:\/\/)?space\.bilibili\.com\/([\d]+)"
ACFUN_USER_SPACE = r"(https:\/\/|http:\/\/)?www\.acfun\.cn\/u\/([\d]+)"
NICOVIDEO_USER_SPACE = r"(https:\/\/|http:\/\/)?(www\.|m\.)?nicovideo\.jp\/user\/([\d]+)"
YOUTUBE_USER_SPACE = r"(https:\/\/|http:\/\/)?(www\.|m\.)?youtube\.com\/channel\/([\d\w]+)"
TWITTER_USER_SPACE = r"(https:\/\/|http:\/\/)?(www\.|m\.)?twitter\.com\/([\d\w]+)"
ZCOOL_USER_SPACE = r"(https:\/\/|http:\/\/)?www\.zcool\.com\.cn\/u\/([\d]+)"

class Bilibili() :
    PATTERN = r"(https:\/\/|http:\/\/)?space\.bilibili\.com\/([\d]+)"
    def extract(self, url) :
        m = re.match(self.PATTERN, url)
        if m :
            return True, 'bilibili-%s' % m.group(2)
        else :
            return False, ''

class Acfun() :
    PATTERN = r"(https:\/\/|http:\/\/)?www\.acfun\.cn\/u\/([\d]+)"
    def extract(self, url) :
        m = re.match(self.PATTERN, url)
        if m :
            return True, 'bilibili-%s' % m.group(2)
        else :
            return False, ''

class Nicovideo() :
    PATTERN = r"(https:\/\/|http:\/\/)?(www\.|m\.)?nicovideo\.jp\/user\/([\d]+)"
    def extract(self, url) :
        m = re.match(self.PATTERN, url)
        if m :
            return True, 'nicovideo-%s' % m.group(3)
        else :
            return False, ''

class Youtube() :
    PATTERN = r"(https:\/\/|http:\/\/)?(www\.|m\.)?youtube\.com\/channel\/([\d\w]+)"
    def extract(self, url) :
        m = re.match(self.PATTERN, url)
        if m :
            return True, 'youtube-%s' % m.group(3)
        else :
            return False, ''

class Twitter() :
    PATTERN = r"(https:\/\/|http:\/\/)?(www\.|m\.)?twitter\.com\/([\d\w]+)"
    def extract(self, url) :
        m = re.match(self.PATTERN, url)
        if m :
            return True, 'twitter-%s' % m.group(3)
        else :
            return False, ''

class Zcool() :
    PATTERN = r"(https:\/\/|http:\/\/)?www\.zcool\.com\.cn\/u\/([\d]+)"
    def extract(self, url) :
        m = re.match(self.PATTERN, url)
        if m :
            return True, 'zcool-%s' % m.group(2)
        else :
            return False, ''

ALL_MATCHERS = [Bilibili(), Acfun(), Nicovideo(), Youtube(), Twitter(), Zcool()]

def createUserSpaceIds(urls) :
    matched_ids = []
    for url in urls :
        for matcher in ALL_MATCHERS :
            matched, userid = matcher.extract(url)
            if matched :
                matched_ids.append(userid)
                break
    return list(set(matched_ids))

def getAuthorRecord(tag, language) :
    tag_obj = tagdb._tag(tag)
    if not 'author' in tag_obj :
        raise UserError('RECORD_NOT_FOUND')
    author_obj = db.authors.find_one({'_id': tag_obj['author']})
    assert author_obj
    author_obj['common_tags'] = tagdb.translate_tag_ids_to_user_language(author_obj['common_tagids'], language)
    return author_obj

def matchUserSpace(urls) :
    """
    Given serval user space URLs from scraper, this function checks if an author in the databases matches that URL
    and return author object so the scraper can add common_tags given by the author object
    """
    if not urls :
        return [], []
    all_matched_ids = createUserSpaceIds(urls)
    all_matched_records = list(db.authors.find({'user_space_ids': {'$in': all_matched_ids}}))
    all_matched_author_tag_objs = list(db.tags.find({'author': {'$in': [x['_id'] for x in all_matched_records]}}))
    return all_matched_records, all_matched_author_tag_objs
