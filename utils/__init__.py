
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

