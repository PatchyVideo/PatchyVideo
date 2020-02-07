
from init import app

import db
import utils
import services
import ajax_backend
#import pages
#import backend

if __name__ == '__main__' or __name__ == 'main' :
    from db import tagdb
    tagdb.init_autocomplete()
    app.run()

