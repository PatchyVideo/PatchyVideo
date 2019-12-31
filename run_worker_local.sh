export FLASK_ENV=development
export REDISTOGO_URL_WORKER=redis://127.0.0.1:6379
export IMAGE_PATH=/home/zyddnys/pvdata/images
export MONGODB_URL=mongodb://127.0.0.1:27017/patchyvideo
export REDISTOGO_URL=127.0.0.1
export ENABLE_TRANSACTION=false
export GOOGLE_API_KEYs=AIzaSyC9veNBmKCVI7CofvXmbt-kOw4jYmQGKzE,AIzaSyD1mnyt3jcTyO5efO8fDy0gYWvXd_V4rVw
python3.7 scraper.py
