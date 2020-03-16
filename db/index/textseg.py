
import itertools
import os

from utils.http import post_raw
from bson.json_util import loads

if os.getenv("FLASK_ENV", "development") == "production" :
	TEXTSEG_ADDRESS = 'http://textseg:5005/'
else :
	TEXTSEG_ADDRESS = 'http://localhost:5005/'

def cut_for_search(txt) :
	resp = post_raw(TEXTSEG_ADDRESS + 's/', txt.encode('utf-8'))
	txt = resp.content.decode('utf-8')
	words = loads(txt)['Words']
	return words

def find_touhou_words(txt) :
	resp = post_raw(TEXTSEG_ADDRESS + 't/', txt.encode('utf-8'))
	txt = resp.content.decode('utf-8')
	words = loads(txt)
	return words

def cut_for_index(txt) :
	if isinstance(txt, list) :
		return list(set(itertools.chain.from_iterable([cut_for_index(i) for i in txt])))
	return loads(post_raw(TEXTSEG_ADDRESS + 'i/', txt.encode('utf-8')).text)['Words']
