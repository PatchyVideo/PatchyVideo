
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
	};
	_URL_MATCHERS["av[\\d]+"] = function(match) {
	};
	_URL_MATCHERS["(https:\\/\\/|http:\\/\\/)?(www\\.)?acfun\\.cn\\/v\\/ac[\\d]+"] = function(match) {
	};
	_URL_MATCHERS["ac[\\d]+"] = function(match) {
	};
	_URL_MATCHERS["(https:\\/\\/|http:\\/\\/)?(www\\.)?nicovideo\\.jp\\/watch\\/(s|n)m[\\d]+"] = function(match) {
	};
	_URL_MATCHERS["(s|n)m[\\d]+"] = function(match) {
	};
	_URL_MATCHERS["(https:\\/\\/(www\\.|m\\.)?youtube\\.com\\/watch\\?v=[-\\w]+|https:\\/\\/youtu\\.be\\/(watch\\?v=[-\\w]+|[-\\w]+))"] = function(match) {
	};
	_URL_MATCHERS["(https:\\/\\/)?(www\\.|mobile\\.)?twitter\\.com\\/[\\w]+\\/status\\/[\\d]+"] = function(match) {
	};
	_URL_EXPANDERS["^ac[\\d]+"] = function(short_link) {
		return "https://www.acfun.cn/v/" + short_link;
	};
	_URL_EXPANDERS["^av[\\d]+"] = function(short_link) {
		return "https://www.bilibili.com/video/" + short_link;
	};
	_URL_EXPANDERS["^(s|n)m[\\d]+"] = function(short_link) {
		return "https://www.nicovideo.jp/watch/" + short_link;
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

function buildUrlTools(url) {
	ret = '';
	ret += `<button onclick='postAsCopy(this, "${url}")'>添加副本</button>`
	return ret;
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
	desc_urlified = desc_text.replace(combined_matcher_regex, function(url) {
		tools_text = `<div class="url-tools">${buildUrlTools(url)}</div>`;
		for (var key in _URL_EXPANDERS) {
			if (new RegExp(key, 'i').test(url)) {
				expanded_url = _URL_EXPANDERS[key](url);
				return `<div class="video-link-div"><a href="${expanded_url}">${url}</a>${tools_text}</div>`;
			}
		}
		return `<div class="video-link-div"><a href="${url}">${url}</a>${tools_text}</div>`;
	});
	desc_obj.html(desc_urlified);
}
