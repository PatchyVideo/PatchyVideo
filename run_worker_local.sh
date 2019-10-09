export FLASK_ENV=development
export REDISTOGO_URL_WORKER=redis://192.168.0.50:6379
export IMAGE_PATH=../images
export MONGODB_URL=mongodb://192.168.0.50:27017/patchyvideo
export REDISTOGO_URL=192.168.0.50
export ENABLE_TRANSACTION=false
python3.7 worker.py
