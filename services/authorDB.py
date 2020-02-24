
from init import rdb
from db import db, tagdb, client
from utils.exceptions import UserError
from utils.dbtools import MongoTransaction
from config import AuthorDB
from services.tcb import filterOperation
from utils.logger import log
from utils.rwlock import usingResource, modifyingResource

from bson import ObjectId

@modifyingResource('tags')
def createOrModifyAuthorRecord(user, author_type, tagid, common_tags, user_spaces, desc, avatar_file_key = None) :
    filterOperation('createOrModifyAuthorRecord', user)
    log(obj = {'author_type': author_type, 'tagid': tagid, 'common_tags': common_tags, 'user_spaces': user_spaces, 'desc': desc, 'avatar_file_key': avatar_file_key})
    if author_type not in ['individual', 'group'] :
        raise UserError('INCORRECT_AUTHOR_TYPE')
    if not isinstance(user_spaces, list) :
        raise UserError('INCORRECT_REQUEST_USER_SPACES')
    if len(desc) > AuthorDB.DESC_MAX_LENGTH :
        raise UserError('DESC_TOO_LONG')
    with MongoTransaction(client) as s :
        tag_obj = tagdb._tag(tagid, session = s())
        if tag_obj['category'] != 'Author' :
            raise UserError('TAG_NOT_AUTHOR')
        existing_record = None
        log(obj = {'tag_obj': tag_obj})
        if 'author' in tag_obj :
            existing_record = db.authors.find_one({'_id': tag_obj['author']}, session = s())
            assert existing_record
            log(obj = {'old_record': existing_record})
        common_tagids = tagdb.filter_and_translate_tags(common_tags, session = s())
        avatar_file = ''
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
                'desc': desc,
                'avatar': avatar_file
            }}, session = s())
        else :
            record_id = db.authors.insert_one({
                'type': author_type,
                'tagid': tagid,
                'common_tagids': common_tagids,
                'urls': user_spaces,
                'desc': desc,
                'avatar': avatar_file
            }, session = s()).inserted_id
            record_id = ObjectId(record_id)
        db.tags.update_one({'_id': tag_obj['_id']}, {'$set': {'author': record_id}})
        s.mark_succeed()
        return str(record_id)

def getAuthorRecord(tag) :
    tag_obj = tagdb._tag(tag)
    if not 'author' in tag_obj :
        raise UserError('RECORD_NOT_FOUND')
    author_obj = db.authors.find_one({'_id': tag_obj['author']})
    assert author_obj
    return author_obj

def matchUserSpace(url) :
    """
    Given a user space URL from scraper, this function checks if an author in the databases matches that URL
    and return author object so the scraper can add common_tags given by the author object
    """
    # TODO
    pass
