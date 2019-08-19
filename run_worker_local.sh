export FLASK_ENV=development
export REDISTOGO_URL_WORKER=redis://localhost:6379
export IMAGE_PATH=pvdata2
export MONGODB_URL=mongodb://localhost:27017/patchyvideo
export REDISTOGO_URL=localhost
export ENABLE_TRANSACTION=false
python worker.py
