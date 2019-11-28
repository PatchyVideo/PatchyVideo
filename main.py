
from init import app

import utils
import db
import services
import ajax_backend
import pages
import backend

if __name__ == '__main__' or __name__ == 'main' :
    from db import tagdb
    import sys
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!! init_autocomplete %s' % __name__, file = sys.stderr)
    tagdb.init_autocomplete()
    app.run()

