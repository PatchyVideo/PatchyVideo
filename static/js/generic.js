
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
            if (result.status == 'SUCCEED')
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
    order = $("#order").attr("content");
    form = $(`<form style="display: none;" action="${window.location.href}" method="GET"><input style="display: none;" name="query" type="text" value="${query}" /><input style="display: none;" name="order" type="text" value="${order}" /><input name="page" type="text" value="${page}" /></form>`);
    $("body").append(form);
    form.submit();
}

function proxyResource(url, referrer = "", user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3835.0 Safari/537.36") {
    url = escape(url);
    if (referrer)
        header = JSON.stringify({ 'Referer' : referrer, 'User-Agent': user_agent })
    else
        header = JSON.stringify({ 'User-Agent': user_agent })
    header = escape(header)
    return `/helper/proxy?url=${url}&header=${header}`;
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

function getUrlVars()
{
    var vars = [], hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++)
    {
        hash = hashes[i].split('=');
        vars.push(hash[0]);
        vars[hash[0]] = hash[1];
    }
    return vars;
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

function copyToClipboard(obj) {
    const el = document.createElement('textarea');
    el.value = obj.text();
    document.body.appendChild(el);
    el.select();
    el.setSelectionRange(0, 99999);
    document.execCommand('copy');
    document.body.removeChild(el);
}

_color_map = {
    'Copyright': '#A0A',
    'Language': '#585455',
    'Character': '#0A0',
    'Author': '#A00',
    'General': '#0073ff',
    'Meta': '#F80'
};

function getCategoryColor(category) {
    return _color_map[category];
}

_color_map_id = {
    2: '#A0A',
    5: '#585455',
    1: '#0A0',
    3: '#A00',
    0: '#0073ff',
    4: '#F80'
};

function getCategoryIdColor(category_id) {
    return _color_map_id[category_id];
}

_LANGUAGE_MAP = {
    "CHS": "简体中文",
	"CHT": "繁體中文",
	"JPN": "日本語",
	"ENG": "English",
	"KOR": "한국어",
	"CSY": "čeština",
	"NLD": "Nederlands",
	"FRA": "français",
	"DEU": "Deutsch",
	"HUN": "magyar nyelv",
	"ITA": "italiano",
	"PLK": "polski",
	"PTB": "português",
	"ROM": "limba română",
	"RUS": "русский язык",
	"ESP": "español",
	"TRK": "Türk dili",
	"VIN": "Tiếng Việt"
}
