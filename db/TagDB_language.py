
VALID_LANGUAGES = {
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

PREFERRED_LANGUAGE_MAP = {
	'CHS': ['CHS', 'CHT', 'JPN', 'ENG'],
	'CHT': ['CHT', 'JPN', 'CHS', 'ENG'],
	'JPN': ['JPN', 'CHT', 'ENG', 'CHS'],
	'ENG': ['ENG', 'JPN']
}

def _getFirstLanguage(tag_obj) :
	for (_, value) in tag_obj['languages'].items() :
		return value

def translateTagToPreferredLanguage(tag_obj, user_language) :
	if user_language not in PREFERRED_LANGUAGE_MAP :
		return _getFirstLanguage(tag_obj)
	lang_map = PREFERRED_LANGUAGE_MAP[user_language]
	for preferred_language in lang_map :
		if preferred_language in tag_obj['languages'] :
			return tag_obj['languages'][preferred_language]
	return _getFirstLanguage(tag_obj)

