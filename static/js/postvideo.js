
EXPANDERS = {}
PARSERS = {}

//////////////////////////////////////////////////////
//    Event Listeners
//////////////////////////////////////////////////////
function onFetchVideo_Click(event) {
    var url = $("#video-url").val();
    ret = checkURL(url);
    if (ret[0]) {
        setStatus("Please wait");
        $("#video-url").val(ret[1]);
        fetchVideo(ret[1]);
    }
    else {
        setStatus("Invalid URL or not support website", "red");
    }
}

function onPostVideoButton_Click(event) {
    if ($("#tab-button-single").hasClass("tab-active")) {
        submitVideoSingle();
    }
    if ($("#tab-button-batch").hasClass("tab-active")) {
        submitVideoBatch();
    }
}


//////////////////////////////////////////////////////
//    jQuery
//////////////////////////////////////////////////////
$(document).ready(function(){
    $("#fetch-video").click(onFetchVideo_Click);
    $("#post-video-button").click(onPostVideoButton_Click);
    buildParsersAndExpanders();
}
);

function autotag(utags) {
    postJSON('/tags/autotag.do', {
        "utags": utags
    },
    function (result) {
        cur_tags = $("#tags").val();
        cur_tags += result.data.tags.join('\n') + '\nauto_tagged\n';
        $("#tags").val(cur_tags);
    });
}

//////////////////////////////////////////////////////
//    Functions
//////////////////////////////////////////////////////
function buildParsersAndExpanders() {
    PARSERS["^(https:\\/\\/|http:\\/\\/)?(www\\.)?bilibili\\.com\\/video\\/av[\\d]+"] = function(responseDOM, responseURL) {
        err = responseDOM.find('div.error-body');
        if (err.length > 0) {
            setVideoMetadata("", "", "");
            setStatus("Error fetching video", "red");
            return;
        }
        thumbnailURL = responseDOM.filter('meta[itemprop="thumbnailUrl"]').attr("content");
        title = responseDOM.find('h1.video-title').attr("title");
        desc = responseDOM.find('div.info.open').text();
        utags = responseDOM.filter('meta[itemprop="keywords"]').attr("content").split(/,/).filter(function(i){return i}).slice(1, -4);
        autotag(utags);
        setVideoMetadata(thumbnailURL, title, desc);
    };
    EXPANDERS["^av[\\d]+"] = function(short_link) {
        return "https://www.bilibili.com/video/" + short_link;
    };
    PARSERS["^(https:\\/\\/|http:\\/\\/)?(www\\.)?acfun\\.cn\\/v\\/[aA][cC][\\d]+"] = function(responseDOM, responseURL) {
        err = responseDOM.find('div.error-body');
        if (err.length > 0) {
            setVideoMetadata("", "", "");
            setStatus("Error fetching video", "red");
            return;
        }
        thumbnailURL = '';
        title = responseDOM.find('h1.title').text();
        desc = responseDOM.filter('div[class="description-container"]').text();
        if (desc == null) {
            desc = responseDOM.find('div[class="J_description"]').text();
        }
        desc = desc.replace(/<br\s*?\/?>/g, '\n');
        utags = responseDOM.filter('meta[name="keywords"]').attr("content").split(/,/).filter(function(i){return i}).slice(1, -4);
        autotag(utags);
        setVideoMetadata(thumbnailURL, title, desc);
    };
    EXPANDERS["^ac[\\d]+"] = function(short_link) {
        return "https://www.acfun.cn/v/" + short_link;
    };
    PARSERS["^(https:\\/\\/|http:\\/\\/)?(www\\.)?nicovideo\\.jp\\/watch\\/(s|n)m[\\d]+"] = function(responseDOM, responseURL) {
        // TODO: handle error
        thumbnailURL = responseDOM.filter('meta[itemprop="thumbnailUrl"]').attr("content");
        if (thumbnailURL == null) {
            thumbnailURL = responseDOM.filter('meta[name="thumbnail"]').attr("content");
        }
        title = responseDOM.filter('meta[itemprop="name"]').attr("content");
        if (title == null) {
            title = responseDOM.filter('meta[property="og:title"]').attr("content");
        }
        desc = responseDOM.filter('meta[itemprop="description"]').attr("content");
        if (desc == null) {
            desc = responseDOM.filter('meta[name="description"]').attr("content");
        }
        utags = responseDOM.filter('meta[property="og:video:tag"]');
        if (utags == null || utags.length == 0) {
            utags = responseDOM.filter('meta[itemprop="og:video:tag"]');
        }
        utags_array = [];
        for (var i = 0; i < utags.length; ++i) {
            utags_array.push($(utags[i]).attr("content"));
        }
        autotag(utags_array);
        setVideoMetadata(thumbnailURL, title, desc);
    };
    EXPANDERS["^(s|n)m[\\d]+"] = function(short_link) {
        return "https://www.nicovideo.jp/watch/" + short_link;
    };
    PARSERS["^(https:\\/\\/(www\\.|m\\.)?youtube\\.com\\/watch\\?v=[-\\w]+|https:\\/\\/youtu\\.be\\/(watch\\?v=[-\\w]+|[-\\w]+))"] = function(responseDOM, responseURL) {
        /*var vidid = "";
        if (responseURL.indexOf("youtube.com") >= 0) {
            var idx = responseURL.lastIndexOf('=');
            vidid = responseURL.substring(idx + 1, responseURL.length);
        } else if (responseURL.indexOf("youtu.be") >= 0) {
            if (responseURL.indexOf("watch?v=") >= 0) {
                var idx = responseURL.lastIndexOf('=');
                vidid = responseURL.substring(idx + 1, responseURL.length);
            }
            else {
                var idx = responseURL.lastIndexOf('/');
                vidid = responseURL.substring(idx + 1, responseURL.length);
            }
        }
        if (isEmpty(vidid)) {
            setVideoMetadata("", "", "");
            setStatus("Error fetching video", "red");
            return;
        }
        thumbnailURL = "https://img.youtube.com/vi/" + vidid + "/hqdefault.jpg";
        info_file_link = proxyResource("https://www.youtube.com/get_video_info?video_id=" + vidid);
        $.get(info_file_link, function(data, status) {
            if (status == "success") {
                //let searchParams = new URLSearchParams(data);
                //player_response = searchParams.get("player_response");
                player_response = getQueryVariable(data, "player_response");
                videoDetails = JSON.parse(player_response)['videoDetails'];
                title = unescape(videoDetails.title).replace(/\+/g, ' ');
                desc = unescape(videoDetails.shortDescription).replace(/\+/g, ' ');
                setVideoMetadata(thumbnailURL, title, desc);
            } else {
                setVideoMetadata("", "", "");
                setStatus("Error fetching video", "red");
                return;
            }
        });*/
        postJSON('/helper/get_ytb_info',
        {
            url: responseURL
        }, function(data){
            setVideoMetadata(data["data"]["thumbnailURL"], data["data"]["title"], data["data"]["desc"]);
            autotag(data["data"]["utags"]);
        }, function(data){
            setVideoMetadata("", "", "");
            setStatus("Error fetching video", "red");
        });
    };
    PARSERS["^(https:\\/\\/)?(www\\.|mobile\\.)?twitter\\.com\\/[\\w]+\\/status\\/[\\d]+"] = function(responseDOM, responseURL) {
        postJSON('/helper/get_twitter_info',
        {
            url: responseURL
        }, function(data){
            setVideoMetadata(data["data"]["thumbnailURL"], data["data"]["title"], data["data"]["desc"]);
        }, function(data){
            setVideoMetadata("", "", "");
            setStatus("Error fetching video", "red");
        });
    };
}

function checkURL(url) {
    var pass = false;
    new_url = ""
    url = url.trim();
    for(var key in EXPANDERS) {
        if (new RegExp(key, 'i').test(url)) {
            url = EXPANDERS[key](url);
            break;
        }
    }
    url = clearURL(url);
    for(var key in PARSERS) {
        if (new RegExp(key, 'i').test(url)) {
            pass = true;
            new_url = url.match(new RegExp(key, 'i'))[0];
            break;
        }
    }
    return [pass, new_url];
}

function dispatchParser(url, responseDOM) {
    for(var key in PARSERS) {
        if (new RegExp(key, 'i').test(url)) {
            PARSERS[key](responseDOM, url);
        }
    }
}

function submitVideoSingle() {
    $("#status2").css("display", "none");
    setStatus("Posting...");
    postJSON("/postvideo.do",
    {
        rank: parseInt($("#rank").attr("content")),
        pid: $("#pid").attr("content"),
        copy: $("#copy").attr("content"),
        url: $("#video-url").val(),
        tags: $("#tags").val().split(/\r?\n/).filter(function(i){return i;})
    },
    function(result){
        $("#status2").css("display", "block");
        $("#result-link").attr("href", "/postresults/" + result['data']['task_id']);
        setStatus("Post succeed, please wait while our server is processing your post.");
    },
    function(result){
        alert(result.data.reason);
        setStatus("Ready");
    });
}

function submitVideoBatch() {
    $("#status2").css("display", "none");
    setStatus("Posting...");
    postJSON("/postvideo_batch.do",
        {
            rank: parseInt($("#rank").attr("content")),
            pid: $("#pid").attr("content"),
            copy: $("#copy").attr("content"),
            videos: $("#video-list").val().split(/\r?\n/).filter(function(i){return i}),
            tags: $("#tags").val().split(/\r?\n/).filter(function(i){return i}),
            as_copies: $("#post-as-copies").is(":checked")
        },
        function(result){
            $("#status2").css("display", "none");
            setStatus("Post succeed, please wait while our server is processing your post.");
        },
        function(result){
            alert(result.data.reason);
            setStatus("Ready");
        }
    );
}

function fetchVideo(url) {
    proxy_url = proxyResource(url, "");
    downloadPage(proxy_url,
        function(result) {
            responseDOM = $(result);
            dispatchParser(url, responseDOM, url);
        },
        function(result) {
            setVideoMetadata("", "", "");
            setStatus("Error fetching video", "red");
        }
    );
}

function setVideoMetadata(thumbnail, title, desc) {
    if (isEmpty(thumbnail)) {
        $("#video-thumbnail").removeAttr("src");
    } else {
        thumbnail_url = proxyResource(thumbnail, "");
        $("#video-thumbnail").attr("src", thumbnail_url);
    }
    $("#video-title").text(title);
    $("#video-description").text(desc);
    setStatus("Ready");
}

function gotoTab(name) {
    $(".tab-element").each(function(idx){
        $(this).css("display", "none");
    });
    $(".tab-button").each(function(idx){
        $(this).removeClass("tab-active");
    });
    $("#tab-" + name).css("display", "block");
    $("#tab-button-" + name).addClass("tab-active");
}
