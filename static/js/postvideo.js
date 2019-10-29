
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
    if ($("#tab-button-single").hasClass("active")) {
        submitVideoSingle();
    }
    if ($("#tab-button-batch").hasClass("active")) {
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

//////////////////////////////////////////////////////
//    Functions
//////////////////////////////////////////////////////
function buildParsersAndExpanders() {
    PARSERS["^(https:\/\/|http:\/\/)?(www\.)?bilibili\.com\/video\/av[\\d]+"] = function(responseDOM, responseURL) {
        err = responseDOM.find('div.error-body');
        if (err.length > 0) {
            setVideoMetadata("", "", "");
            setStatus("Error fetching video", "red");
            return;
        }
        thumbnailURL = responseDOM.filter('meta[itemprop="thumbnailUrl"]').attr("content");
        title = responseDOM.find('h1.video-title').attr("title");
        desc = responseDOM.find('div.info.open').text();
        setVideoMetadata(thumbnailURL, title, desc);
    };
    EXPANDERS["^av[\\d]+"] = function(short_link) {
        return "https://www.bilibili.com/video/" + short_link;
    };
    PARSERS["^^(https:\\/\\/|http:\\/\\/)?(www\.)?nicovideo\\.jp\\/watch\\/sm[\\d]+"] = function(responseDOM, responseURL) {
        // TODO: handle error
        thumbnailURL = responseDOM.filter('meta[itemprop="thumbnailUrl"]').attr("content");
        title = responseDOM.filter('meta[itemprop="name"]').attr("content");
        desc = responseDOM.filter('meta[itemprop="description"]').attr("content");
        setVideoMetadata(thumbnailURL, title, desc);
    };
    EXPANDERS["^sm[\\d]+"] = function(short_link) {
        return "https://www.nicovideo.jp/watch/" + short_link;
    };
    PARSERS["^(https:\\/\\/(www\\.|m\\.)?youtube\\.com\\/watch\\?v=[-\\w]+|https:\\/\\/youtu\\.be\\/(watch\\?v=[-\\w]+|[-\\w]+))"] = function(responseDOM, responseURL) {
        var vidid = "";
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
        thumbnailURL = "https://img.youtube.com/vi/" + vidid + "/maxresdefault.jpg";
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
        });
    };
    PARSERS["^(https:\\/\\/)?(www\\.|mobile\\.)?twitter\\.com\\/[\\w]+\\/status\\/[\\d]+"] = function(responseDOM, responseURL) {
        postJSON('/helper/get_twitter_info.do',
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
        if (new RegExp(key).test(url)) {
            url = EXPANDERS[key](url);
            break;
        }
    }
    url = clearURL(url);
    for(var key in PARSERS) {
        if (new RegExp(key).test(url)) {
            pass = true;
            new_url = url.match(new RegExp(key))[0];
            break;
        }
    }
    return [pass, new_url];
}

function dispatchParser(url, responseDOM) {
    for(var key in PARSERS) {
        if (new RegExp(key).test(url)) {
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
        tags: $("#tags").val().split(/\r?\n/).filter(function(i){return i})
    },
    function(result){
        $("#status2").css("display", "block");
        $("#result-link").attr("href", "/postresults/" + result['data']['task_id']);
        setStatus("Post succeed, please wait while our server is processing your post.");
    },
    function(result){
        alert(result.data);
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
            tags: $("#tags").val().split(/\r?\n/).filter(function(i){return i})
        },
        function(result){
            $("#status2").css("display", "none");
            setStatus("Post succeed, please wait while our server is processing your post.");
        },
        function(result){
            alert(result.data);
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
        $(this).removeClass("active");
    });
    $("#tab-" + name).css("display", "block");
    $("#tab-button-" + name).addClass("active");
}
