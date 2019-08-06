
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



