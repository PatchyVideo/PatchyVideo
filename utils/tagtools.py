
import re
from db.query_parser.Parser import _lex

_match_object = re.compile(r"^[\w][\w][\w_\!\-']*(_\([\w'\!\-_]+\))?$")
_match_language_object = re.compile(r"^[\w]{4,}$")
_color_map = {
    'Copyright': '#A0A',
    'Language': '#585455',
    'Character': '#0A0',
    'Author': '#A00',
    'General': '#0073ff',
    'Meta': '#F80'}

def verifyAndSanitizeTagOrAlias(alias):
    alias = alias.strip()
    try:
        ts, ss = _lex(alias)
    except:
        return False, ''
    if len(ts) == 1 :
        alias = ss[0].lower()
        if ts[0] == 'TAG':
            if any(ban in alias for ban in [':', '>', '<', '=', '-', '~', '+', '*', '/', '.', ',', ';', ':']) : # special symbols
                return False, ''
            if alias in ['site', 'date', 'and', 'or', 'not', 'any', 'all', 'notag', 'true', 'false'] : # keywords
                return False, ''
            return True, alias
    return False, ''

def verifyAndSanitizeLanguage(lang):
    lang = lang.strip()
    if len(lang) <= 2 :
        return False, ''
    ret = _match_language_object.match(lang)
    if ret:
        lang_sanitized = ret.group(0)
        return True, lang_sanitized
    return False, ''

def getTagColor(tags, tag_category_map):
    ans = {}
    for tag in tags:
        if tag in tag_category_map:
            ans[tag] = _color_map[tag_category_map[tag]]
    return ans
