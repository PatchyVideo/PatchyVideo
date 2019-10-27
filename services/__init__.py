
import os

if os.getenv("FLASK_ENV", "development") == "production" :
    TAG_TRACKER_ADDRESS = 'http://tagtracker:5001'
else :
    TAG_TRACKER_ADDRESS = 'http://localhost:5001'

