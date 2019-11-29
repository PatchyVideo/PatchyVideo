set FLASK_ENV=development
set REDISTOGO_URL_WORKER=redis://192.168.99.100:6379
set IMAGE_PATH=E:\pvdata2
set MONGODB_URL=mongodb://192.168.99.100:27017/patchyvideo
set REDISTOGO_URL=192.168.99.100
set ENABLE_TRANSACTION=false
python scraper.py
pause