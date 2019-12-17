
$(document).ready(function() {
	tbn_url = $("#thumbnail-url").attr("content");
	query_str = $("#query").attr("content");
	$("#search-bar-query").val(query_str);
	$("#edit-current-tags").css("display", "inline");
	$("#edit-current-tags").attr("href", "javascript:showModal();");
	buildUrlMatchers();
	urlifyDesc();
});

function breaklink() {
	postJSON("/videos/breaklink.do",
	{
		"video_id": $("#video-id").attr("content"),
	}, function(result)
	{
		location.reload();
	});
}

function syncTags(dst, src) {
	postJSON("/videos/synctags.do",
	{
		"src": src,
		"dst": dst
	}, function(result)
	{
		location.reload();
	});
}

function refreshVideo(vid) {
	postJSON("/videos/refresh.do",
	{
		"video_id": vid
	}, function(result)
	{
		location.reload();
	});
}

function broadcastTags(src) {
	postJSON("/videos/broadcasttags.do",
	{
		"src": src
	}, function(result)
	{
		location.reload();
	});
}

function createPlaylistFromSingleVideo(vid) {
	console.log(vid);
}

_URL_MATCHERS = {};
_URL_EXPANDERS = {};

function buildUrlMatchers() {
	_URL_MATCHERS["(https:\\/\\/|http:\\/\\/)?(www\\.)?bilibili\\.com\\/video\\/av[\\d]+"] = function(match) {
		return [match, "video"];
	};
	_URL_MATCHERS["(https:\\/\\/|http:\\/\\/)?(www\\.)?acfun\\.cn\\/v\\/ac[\\d]+"] = function(match) {
		return [match, "video"];
	};
	_URL_MATCHERS["(https:\\/\\/|http:\\/\\/)?(www\\.)?nicovideo\\.jp\\/watch\\/(s|n)m[\\d]+"] = function(match) {
		return [match, "video"];
	};
	_URL_MATCHERS["((https:\\/\\/)?(www\\.|m\\.)?youtube\\.com\\/watch\\?v=[-\\w]+|https:\\/\\/youtu\\.be\\/(watch\\?v=[-\\w]+|[-\\w]+))"] = function(match) {
		return [match, "video"];
	};
	_URL_MATCHERS["(https:\\/\\/)?(www\\.|mobile\\.)?twitter\\.com\\/[\\w]+\\/status\\/[\\d]+"] = function(match) {
		return [match, "video"];
	};
	_URL_MATCHERS["ac[\\d]+"] = function(short_link) {
		return ["https://www.acfun.cn/v/" + short_link, "video"];
	};
	_URL_MATCHERS["av[\\d]+"] = function(short_link) {
		return ["https://www.bilibili.com/video/" + short_link, "video"];
	};
	_URL_MATCHERS["(s|n)m[\\d]+"] = function(short_link) {
		return ["https://www.nicovideo.jp/watch/" + short_link, "video"];
	};
	_URL_MATCHERS["youtube-[-\\w]+"] = function(short_link) {
		return ["https://www.youtube.com/watch?v=" + short_link.substring(8), "video"];
	};
	_URL_MATCHERS["mylist\\/[\\d]+"] = function(short_link) {
		return ["https://www.nicovideo.jp/" + short_link, "playlist"];
	};
}

function postAsCopy(sender, url) {
	btn = $(sender);
	btn.text("请稍候");
	btn.click(function(){});
	postJSON("/postvideo.do",
	{
		"url": url,
		"tags": $("#tags").attr("content").split(/\s/).filter(function(i){return i;}),
		"copy": $("#video-id").attr("content")
	}, function(result)
	{
		btn.text("查看");
		btn.click(function(){window.open('/postresults/' + result.data.task_id);});
	});
}

function buildUrlTools(logged_in, url, link_type) {
	if (!logged_in) {
		return '';
	}
	
	if (link_type == "video") {
		ret = `<div class="url-tools">`;
		ret += `<button onclick='postAsCopy(this, "${url}")'>添加副本</button>`
		ret += `</div>`;
		return ret;
	}
	/*else if (link_type == "playlist") {
		ret += `<button onclick='postPlaylist(this, "${url}")'>添加播放列表</button>`;
	}*/
	return '';
}

function urlifyDesc() {
	desc_obj = $("#desc-area");
	desc_text = desc_obj.text();
	combined_matcher = '(';
	var i = 1;
	for (var regex in _URL_MATCHERS) {
		if (i == Object.keys(_URL_MATCHERS).length) {
			combined_matcher += regex;
		} else {
			combined_matcher += regex + '|';
		}
		i += 1;
	}
	combined_matcher += ')';
	combined_matcher_regex = new RegExp(combined_matcher, 'ig');
	is_logged_in = !isEmpty($("#user-id").attr("content"));
	desc_urlified = desc_text.replace(combined_matcher_regex, function(url) {
		for (var key in _URL_MATCHERS) {
			if (new RegExp(key, 'i').test(url)) {
				const [expanded_url, link_type] = _URL_MATCHERS[key](url);
				return `<div class="video-link-div"><a href="${expanded_url}">${url}</a>${buildUrlTools(is_logged_in, expanded_url, link_type)}</div>`;
			}
		}
	});
	desc_obj.html(desc_urlified);
}
