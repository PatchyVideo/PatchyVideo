
import re
from db.query_parser.Parser import _lex

_match_object = re.compile(r"^[\w][\w][\w_\!\-']*(_\([\w'\!\-_]+\))?$")

_color_map = {
	'Copyright': '#A0A',
	'Language': '#585455',
	'Character': '#0A0',
	'Author': '#A00',
	'General': '#0073ff',
	'Meta': '#F80',
	'Soundtrack': '#FF7792'}

def verifyAndSanitizeTagOrAlias(alias):
	alias = alias.strip()
	try:
		ts, ss = _lex(alias)
	except:
		return False, ''
	if len(ts) == 1 :
		alias = ss[0]
		if ts[0] == 'TAG':
			if any(ban in alias for ban in [':', '>', '<', '=', '~', '+', '*', '/', ',', ';', ':', '\"', '\n', '\r', '\v', '\f', '\t', ' ']) : # special symbols
				return False, ''
			if alias.lower() in ['site', 'date', 'placeholder', 'and', 'or', 'not', 'any', 'all', 'tags', 'true', 'false'] : # keywords
				return False, ''
			return True, alias
	return False, ''

_VALID_LANGUAGES = {
	"CHS": "Chinese (Simplified)",
	"CHT": "Chinese (Traditional)",
	"CSY": "Czech",
	"NLD": "Dutch",
	"ENG": "English",
	"FRA": "French",
	"DEU": "German",
	"HUN": "Hungarian",
	"ITA": "Italian",
	"JPN": "Japanese",
	"KOR": "Korean",
	"PLK": "Polish",
	"PTB": "Portuguese (Brazil)",
	"ROM": "Romanian",
	"RUS": "Russian",
	"ESP": "Spanish",
	"TRK": "Turkish",
	"VIN": "Vietnamese"
}

def verifyAndSanitizeLanguage(lang):
	if lang in _VALID_LANGUAGES :
		return True, lang
	else :
		return False, ''

def getTagColor(tags, tag_category_map):
	ans = {}
	for tag in tags:
		if tag in tag_category_map:
			ans[tag] = _color_map[tag_category_map[tag]]
	return ans

_PREFERRED_LANGUAGE_MAP = {
	'CHS': ['CHS', 'CHT', 'JPN', 'ENG'],
	'CHT': ['CHT', 'JPN', 'CHS', 'ENG'],
	'JPN': ['JPN', 'CHT', 'ENG', 'CHS'],
	'ENG': ['ENG', 'JPN']
}

def translateTagsToPreferredLanguage(tag_objs, user_language) :
	if user_language not in _PREFERRED_LANGUAGE_MAP :
		return [obj['tag'] for obj in tag_objs]
	lang_map = _PREFERRED_LANGUAGE_MAP[user_language]
	ret = []
	for tag_obj in tag_objs :
		if 'language' in tag_obj and tag_obj['language'] == user_language :
			ret.append(tag_obj['tag'])
			continue
		found_preferred_language = False
		if 'languages' in tag_obj :
			for preferred_language in lang_map :
				if 'language' in tag_obj and tag_obj['language'] == preferred_language :
					ret.append(tag_obj['tag'])
					found_preferred_language = True
					break
				if preferred_language in tag_obj['languages'] :
					ret.append(tag_obj['languages'][preferred_language])
					found_preferred_language = True
					break
		if not found_preferred_language :
			ret.append(tag_obj['tag'])
	return ret

def getTagObjects(tagdb, tags) :
	return [obj for obj in tagdb.db.tags.find({'tag': {'$in': tags}})]
