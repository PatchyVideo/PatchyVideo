

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

	def AddTags(self, list_of_tuple_of_tag_category_count) :
		payload = "%d " % len(list_of_tuple_of_tag_category_count)
		for (tag, category, count) in list_of_tuple_of_tag_category_count :
			payload += tag + " " + category + (" %d " % count)
		self._post("AddTags", "addwords", payload)

	def AddAlias(self, list_of_tuple_of_src_dst) :
		payload = "%d " % len(list_of_tuple_of_src_dst)
		for (src, dst) in list_of_tuple_of_src_dst :
			payload += src + " " + dst + " "
		self._post("AddAlias", "addalias", payload)

	def SetTagOrAliasCount(self, list_of_tuple_of_tag_count) :
		payload = "%d " % len(list_of_tuple_of_tag_count)
		for (tag, count) in list_of_tuple_of_tag_count :
			payload += tag + (" %d " % count)
		self._post("SetTagOrAliasCount", "setwords", payload)

	def SetTagOrAliasCountDiff(self, list_of_tuple_of_tag_diff) :
		payload = "%d " % len(list_of_tuple_of_tag_diff)
		for (tag, diff) in list_of_tuple_of_tag_diff :
			payload += tag + (" %d " % diff)
		self._post("SetTagOrAliasCountDiff", "setwordsdiff", payload)

	def DeleteTagOrAlias(self, tag_or_alias) :
		payload = tag_or_alias + " "
		self._post("DeleteTagOrAlias", "delword", payload)

	def DeleteAlias(self, alias) :
		payload = alias + " "
		self._post("DeleteAlias", "delalias", payload)

