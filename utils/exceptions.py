
class UserError(Exception) :
	def __init__(self, msg, aux = None) :
		self.msg = msg
		self.aux = aux

class ScraperError(Exception) :
	def __init__(self) :
		pass

import sys
from functools import wraps

def noexcept(func) :
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			ret = func(*args, **kwargs)
			return ret
		except Exception as ex:
			print(ex, file = sys.stderr)
		return None
	return wrapper
