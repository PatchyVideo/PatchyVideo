
import re
from db.query_parser.Parser import _lex

_pattern = "^[\\w]+$"

def verifyAndSanitizeTag(tag):
    ts, ss = _lex(tag)
    if len(ts) == 1 :
        return ts[0] == 'TAG', ss[0]
    return False, ''

