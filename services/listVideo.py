
from db import tagdb as db
from .tagStatistics import getPopularTags, getCommonTags, updateTagSearch
from spiders import dispatch_no_expand

def listVideoQuery(query_str, page_idx, page_size, order = 'latest'):
	query_obj, tags = db.compile_query(query_str)
	updateTagSearch(tags)
	if query_obj == "INCORRECT_QUERY":
		return "failed", None, [], 0
	result = db.retrive_items(query_obj)
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	ret = result.skip(page_idx * page_size).limit(page_size)
	count = ret.count()
	videos = [item for item in ret]
	return "success", videos, getCommonTags(videos), count

def listVideo(page_idx, page_size, order = 'latest'):
	result = db.retrive_items({})
	if order == 'latest':
		result = result.sort([("meta.created_at", -1)])
	if order == 'oldest':
		result = result.sort([("meta.created_at", 1)])
	return result.skip(page_idx * page_size).limit(page_size), getPopularTags()

