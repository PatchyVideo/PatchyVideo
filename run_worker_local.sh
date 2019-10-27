export FLASK_ENV=development
export REDISTOGO_URL_WORKER=redis://127.0.0.1:6379
export IMAGE_PATH=../images
export MONGODB_URL=mongodb://127.0.0.1:27017/patchyvideo
export REDISTOGO_URL=127.0.0.1
export ENABLE_TRANSACTION=false
python3.7 worker.py
