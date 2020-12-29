
"""
Package:
    utils
Location:
    /utils
Description:
    Helper functions and interceptors go here
"""

class Namespace():
    @staticmethod
    def create_from_dict(d):
        ret = Namespace()
        ret.__dict__.update(d)
        return ret

def getDefaultJSON(data, name, default_value) :
    if hasattr(data, name) :
        val = getattr(data, name)
        if val is not None :
            return type(default_value)(val)
    return default_value

def getOffsetLimitJSON(data) :
    if hasattr(data, 'page') and (hasattr(data, 'page_size') or hasattr(data, 'pageSize')) :
        page = int(getattr(data, 'page'))
        page_size = int(getattr(data, 'page_size') or getattr(data, 'pageSize'))
        return max(page - 1, 0) * page_size, page_size
    if hasattr(data, 'offset') and hasattr(data, 'limit') :
        offset = int(getattr(data, 'offset'))
        limit = int(getattr(data, 'limit'))
        return offset, limit
    elif hasattr(data, 'limit') :
        limit = int(getattr(data, 'limit'))
        return 0, limit
    return 0, 1
