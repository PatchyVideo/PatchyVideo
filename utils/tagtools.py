
import re
from db.query_parser.Parser import _lex

_pattern = "^[\\w]+$"
_color_map = {
    'Copyright': '#A0A',
    'Language': '#585455',
    'Character': '#0A0',
    'Author': '#A00',
    'General': '#0073ff',
    'Meta': '#F80'}

def verifyAndSanitizeTag(tag):
    ts, ss = _lex(tag)
    if len(ts) == 1 :
        return ts[0] == 'TAG', ss[0]
    return False, ''

def getTagColor(tag_category_map):
    return {tag: _color_map[tag_category_map[tag]] for tag in tag_category_map.keys()}
