# PatchyVideo
The name is short for Patchouli's video library.  
Let me know if you have a better name.
# Why
It is well known that NicoNico as a primary platform for many Touhou contents has fallen behind in all aspects and many creators have moved to either YouTube, but YouTube has two key disadvatages:  
1. As the largest UGC video platform in the world, it is designed to serve the most people, not small communities. For example it is hard to find new creator's work without explicitly searching for it(or its topic) and sort by date or recommended by either someone else or YouTube's algorithm.
2. It is just one platform. Many works are not uploaded to it instead they go to other places(e.g. Bilibili) for some reasons.  

So it would be nice if someone could index videos from different sites together in a way that can be easily searched.  
The solution: a video booru.  
Just like an image booru is designed to meet different people's taste of drawings, a video booru can be used to search for video of interest by utilizing the site's powerful tagging system.  
And this site can serve more than just content consumers, but also content creators by providing a way they can publish their works which does not require social media(you need followers or retweet for others to see). This is important for new creators.
# Primary Features
Must have when the site is offically launched.
1. Basic video posting services. One can give it a video URL and it will automatically download the three defining field of a video: title, description and cover image.
2. A powerful tagging system and tag search engine to ensure you can search whatever you like.
3. Playlists. Just like a YouTube playlist, user can create, edit, subscript to a playlist with an optional cover image for playlist. Playlists can be founded either via playlist list or in videos included in them.
4. Copies. A video can have multiple copies. This happens when people repost it onto different sites(repost touhou MMD from nico to bilibli) or post a subbed version of a video. The copies feature makes it easy to navigate between different copies of the same videos.
# Secondary Features
Optional features.
1. Jsproxy for users from mainland China. So they can view videos on Niconico/YouTube without downloading a proxy/VPN tool.
2. Tag subscription. Subscript to tags(tag querys) you like to see the latest videos.
# Supported Websites
|Site|Status|
|----|-------------|
|Bilibili|Fully Supported|
|Nicovideo|Fully Supported|
|YouTube|Fully Supported|
|Twitter|Planned|
Let me know if you want to add more sites to this list.
# Future Features
Even more optional. Realization of the following features is not guaranteed.  
1. Tag autocomplete. Common found in image booru sites, helps user entering tags.
2. Auto tag. Generate tags from video title and description. Can be done using simple(traditional) NLP algorithms.
3. Danmaku. YouTube don't have danmaku, but one can also install some kind of browser extension.
4. Comment section. Comments are disabled on some videos, we are here to bring it back.
5. Video downloading. Download video via this site. This is very unlikely to happen due to bandwidth issues.
6. Multi-language support. Tags are to be in multiple languages. So is the site.
# Todo list
See [here](./TODO.md)
# Running locally for developers
1. Install docker
2. Install VSCode
3. Install Python 3.7
4. Create a folder for the database
5. Install dependencies by running `pip3 install -r requirements.txt`
6. Run MongoDB with `docker run -d --name db -p 27017:27017 -v <path-to-data-storage>:/data/db mongo`
7. Run Redis with `docker run -d --name redis -p 6379:6379 redis`
8. Run redis-queue worker using `python3 worker.py`
9. Run PatchyVideo by going to VSCode's debug tab, select `Local Run` and run it
10. You can access this local version of PatchyVideo by visiting `localhost:5000`
# Contacts
Please join our QQ group 757676234 for discussions.