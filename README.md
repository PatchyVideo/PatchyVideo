# VUE前端/VUE Frontend
[点这里](https://github.com/suwadaimyojin/patchyvideo-vue)
# 中文部署教程
[点这里](./项目的本地部署.docx)
# 其他微服务/Microservices
1. [分词器/Text Segmentor](https://github.com/zyddnys/PatchyVideo-textseg)
2. [自动补全/Auto-complete](https://github.com/zyddnys/PatchyVideo-autocomplete)
# Running locally for developers
1. Install docker
2. Install VSCode
3. Install Python 3.7
4. Create a folder for the database
5. Install dependencies by running `pip3 install -r requirements.txt`
6. Run MongoDB with `docker run -d --name db -p 27017:27017 -v <path-to-data-storage>:/data/db mongo`
7. Run Redis with `docker run -d --name redis -p 6379:6379 redis`
8. Change `run_worker_local.bat`'s content to your setting
9. Run Scraper worker using `./run_worker_local.bat`
10. Run PatchyVideo by going to VSCode's debug tab, select `Local Run` and run it
11. You can access this local version of PatchyVideo by visiting `localhost:5000`
# Contacts
Please join our QQ group 757676234 for discussions.
Or discord server https://discord.gg/FtPPQqz