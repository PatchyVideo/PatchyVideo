
function isEmpty(str) {
    return (!str || 0 === str.length);
}

function postJSON(url, data, success, error = null, complete = null) {
    $.ajax({
        type: "POST",
        url: url,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function (result) {
            if (result.status == 'success')
                success(result);
            else
                error(result);
        },
        error: error,
        complete: complete
    });
}

function downloadPage(url, success, error = null, complete = null) {
    $.ajax({
        type: "GET",
        url: url,
        success: success,
        error: error,
        complete: complete
    })
}

function gotoPage(page) {
    query = $("#query").attr("content");
    form = $(`<form style="display: none;" action="${window.location.href}" method="POST"><input style="display: none;" name="query" type="text" value="${query}" /><input name="page" type="text" value="${page}" /></form>`);
    $("body").append(form);
    form.submit();
}

function proxyResource(url, referrer = "", user_agent = "Mozilla/5.0 (X11; Ubuntu; Linu…) Gecko/20100101 Firefox/65.0") {
    url = encodeURI(url);
    if (referrer)
        header = JSON.stringify({ 'Referer' : referrer, 'User-Agent': user_agent })
    else
        header = JSON.stringify({ 'User-Agent': user_agent })
    header = encodeURI(header)
    return `/proxy?url=${url}&header=${header}`;
}

function setStatus(prompt, color = "black") {
    $("#status").text(prompt);
    $("#status").css('color', color);
}

function getQueryVariable(query, variable) {
    var vars = query.split('&');
    for (var i = 0; i < vars.length; i++) {
        var pair = vars[i].split('=');
        if (decodeURIComponent(pair[0]) == variable) {
            return decodeURIComponent(pair[1]);
        }
    }
    console.log('Query variable %s not found', variable);
}

function addHTTP(url) {
    if (!/^(?:f|ht)tps?\:\/\//.test(url)) {
        url = "http://" + url;
    }
    return url;
}

function clearURL(url) {
    url_parsed = new URL(addHTTP(url));
    return "https://" + url_parsed.host + url_parsed.pathname + url_parsed.search;
}
