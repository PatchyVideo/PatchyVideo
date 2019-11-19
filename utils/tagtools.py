
import re
from db.query_parser.Parser import _lex

_match_object = re.compile(r"^[\w][\w_\-']*(_\([\w'\-_]+\))?$")
_color_map = {
    'Copyright': '#A0A',
    'Language': '#585455',
    'Character': '#0A0',
    'Author': '#A00',
    'General': '#0073ff',
    'Meta': '#F80'}

"""
def verifyAndSanitizeTag(tag):
    try:
        ts, ss = _lex(tag)
    except:
        return False, ''
    if len(ts) == 1 :
        tag = ss[0].lower()
        if ts[0] == 'TAG':
            if any(ban in tag for ban in [':', '>', '<', '=', '-', '~', '+', '*', '/', '.', ',', ';', ':']) : # special symbols
                return False, ''
            if tag in ['site', 'date', 'and', 'or', 'not', 'any', 'all'] : # keywords
                return False, ''
            return True, tag
    return False, ''
"""

def verifyAndSanitizeTag(tag):
    tag = tag.strip()
    if len(tag) <= 2 :
        return False, ''
    ret = _match_object.match(tag)
    if ret:
        tag_sanitized = ret.group(0)
        if tag_sanitized in ['site', 'date', 'and', 'or', 'not', 'any', 'all'] : # keywords
            return False, ''
        return True, tag_sanitized
    return False, ''

def getTagColor(tags, tag_category_map):
    ans = {}
    for tag in tags:
        if tag in tag_category_map:
            ans[tag] = _color_map[tag_category_map[tag]]
    return ans
