
from db import tagdb as db

def listVideoQuery(query_str, page_idx, page_size, order = 'latest'):
    query_obj = db.compile_query(query_str)
    if query_obj == "INCORRECT_QUERY":
        return "failed", None
    result = db.retrive_items(query_obj)
    if order == 'latest':
        result = result.sort([("meta.created_at", -1)])
    if order == 'oldest':
        result = result.sort([("meta.created_at", 1)])
    return "success", result.skip(page_idx * page_size).limit(page_size)

def listVideo(page_idx, page_size, order = 'latest'):
    result = db.retrive_items({})
    if order == 'latest':
        result = result.sort([("meta.created_at", -1)])
    if order == 'oldest':
        result = result.sort([("meta.created_at", 1)])
    return result.skip(page_idx * page_size).limit(page_size)

