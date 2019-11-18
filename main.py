
from init import app


import utils
import db
import services
import ajax_backend
import pages


if __name__ == '__main__':
    from db import tagdb
    tagdb.init_autocomplete()
    app.run()

