

import sys
import os

from utils.http import post_raw, get_page

if os.getenv("FLASK_ENV", "development") == "production" :
    AUTOCOMPLETE_ADDRESS = 'http://autocomplete:5002'
else :
    AUTOCOMPLETE_ADDRESS = 'http://localhost:5002'

class AutocompleteInterface() :
	def __init__(self, retry_count = 1) :
		self.retry_count = retry_count

	def _post(self, func, endpoint, payload) :
		err_msg = ''
		print(payload, file = sys.stderr)
		for _ in range(self.retry_count) :
			try :
				return post_raw(AUTOCOMPLETE_ADDRESS + "/" + endpoint, payload.encode('utf-8'))
			except Exception as e :
				err_msg = str(e)
		print('FAILED: %s message=%s' % (func, err_msg), file = sys.stderr)

	def AddTag(self, list_of_tuple_of_tagid_count_category) :
		if not list_of_tuple_of_tagid_count_category :
			return
		payload = "%d " % len(list_of_tuple_of_tagid_count_category)
		for (tagid, count, category) in list_of_tuple_of_tagid_count_category :
			payload += "%d %d %s " % (tagid, count, category)
		self._post("AddTag", "addtag", payload)

	def AddWord(self, list_of_tuple_of_tagid_word_lang) :
		if not list_of_tuple_of_tagid_word_lang :
			return
		payload = "%d " % len(list_of_tuple_of_tagid_word_lang)
		for (tagid, word, lang) in list_of_tuple_of_tagid_word_lang :
			payload += "%d %s %s " % (tagid, word, lang)
		self._post("AddWord", "addword", payload)

	def SetCount(self, list_of_tuple_of_tagid_count) :
		if not list_of_tuple_of_tagid_count :
			return
		payload = "%d " % len(list_of_tuple_of_tagid_count)
		for (tagid, count) in list_of_tuple_of_tagid_count :
			payload += "%d %d " % (tagid, count)
		self._post("SetCount", "setcount", payload)

	def SetCountDiff(self, list_of_tuple_of_tagid_diff) :
		if not list_of_tuple_of_tagid_diff :
			return
		payload = "%d " % len(list_of_tuple_of_tagid_diff)
		for (tagid, diff) in list_of_tuple_of_tagid_diff :
			payload += "%d %d " % (tagid, diff)
		self._post("SetCountDiff", "setcountdiff", payload)

	def SetCat(self, list_of_tuple_of_tagid_cat) :
		if not list_of_tuple_of_tagid_cat :
			return
		payload = "%d " % len(list_of_tuple_of_tagid_cat)
		for (tagid, cat) in list_of_tuple_of_tagid_cat :
			payload += "%d %s " % (tagid, cat)
		self._post("SetCat", "setcat", payload)

	def DeleteTag(self, tagid) :
		payload = "%d" % tagid
		self._post("DeleteTag", "deltag", payload)

	def DeleteWord(self, word) :
		payload = word
		self._post("DeleteWord", "delword", payload)

	def MatchFirstTag(self, list_of_querys) :
		if not list_of_querys :
			return
		payload = "%d " % len(list_of_querys)
		for q in list_of_querys :
			payload += "%s " % q
		return self._post("MatchFirstTag", "matchfirst", payload)

class AutocompleteInterfaceDummy() :
	def __init__(self, retry_count = 3) :
		pass

	def _post(self, func, endpoint, payload) :
		pass

	def AddTag(self, list_of_tuple_of_tagid_count_category) :
		pass

	def AddWord(self, list_of_tuple_of_tagid_word_lang) :
		pass

	def SetCount(self, list_of_tuple_of_tagid_count) :
		pass

	def SetCountDiff(self, list_of_tuple_of_tagid_diff) :
		pass

	def SetCat(self, list_of_tuple_of_tagid_cat) :
		pass

	def DeleteTag(self, tagid) :
		pass

	def DeleteWord(self, word) :
		pass

	def MatchFirstTag(self, list_of_querys) :
		pass


