
from init import app

import utils
import db
import services
import ajax_backend
import pages
import backend

if __name__ == '__main__' or __name__ == 'main' :
    from db import tagdb
    tagdb.init_autocomplete()
    app.run()

