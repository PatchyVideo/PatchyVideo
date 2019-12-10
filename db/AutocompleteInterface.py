

import sys
import os

from utils.http import post_raw, get_page

if os.getenv("FLASK_ENV", "development") == "production" :
    AUTOCOMPLETE_ADDRESS = 'http://autocomplete:5002'
else :
    AUTOCOMPLETE_ADDRESS = 'http://localhost:5002'

class AutocompleteInterface() :
	def __init__(self, retry_count = 3) :
		self.retry_count = retry_count

	def _post(self, func, endpoint, payload) :
		err_msg = ''
		for _ in range(self.retry_count) :
			try :
				post_raw(AUTOCOMPLETE_ADDRESS + "/" + endpoint, payload.encode('utf-8'))
				return
			except Exception as e :
				err_msg = str(e)
		print('FAILED: %s message=%s' % (func, err_msg), file = sys.stderr)

	def AddTag(self, list_of_tuple_of_tagid_count_category) :
		payload = "%d " % len(list_of_tuple_of_tagid_count_category)
		for (tagid, count, category) in list_of_tuple_of_tagid_count_category :
			payload += "%d %d %d " % (tagid, count, category)
		self._post("AddTag", "addtag", payload)

	def AddWord(self, list_of_tuple_of_tagid_word) :
		payload = "%d " % len(list_of_tuple_of_tagid_word)
		for (tagid, word) in list_of_tuple_of_tagid_word :
			payload += "%d %s " % (tagid, word)
		self._post("AddWord", "addword", payload)

	def SetCount(self, list_of_tuple_of_tagid_count) :
		payload = "%d " % len(list_of_tuple_of_tagid_count)
		for (tagid, count) in list_of_tuple_of_tagid_count :
			payload += "%d %d " % (tagid, count)
		self._post("SetCount", "setcount", payload)

	def SetCountDiff(self, list_of_tuple_of_tagid_diff) :
		payload = "%d " % len(list_of_tuple_of_tagid_diff)
		for (tagid, diff) in list_of_tuple_of_tagid_diff :
			payload += "%d %d " % (tagid, diff)
		self._post("SetCountDiff", "setcountdiff", payload)

	def DeleteTag(self, tagid) :
		payload = "%d " % tagid
		self._post("DeleteTag", "deltag", payload)

	def DeleteWord(self, word) :
		payload = word + " "
		self._post("DeleteWord", "delword", payload)

