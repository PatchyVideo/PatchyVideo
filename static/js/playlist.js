
//////////////////////////////////////////////////////
//    jQuery
//////////////////////////////////////////////////////
$(document).ready(function(){
    //page_obj = buildPageSelector(parseInt(getMeta("page")), parseInt(getMeta("page-count")));
    //$("div.video-list").append(page_obj);
}
);

function getMeta(id) {
    return $(`#${id}`).attr("content");
}

function buildPageSelector(selected_page, page_count) {
    if (selected_page > page_count || page_count < 1)
        return null;
    p_obj = $(`<p class="page-selector"></p>`);
    if (page_count == 1) {
        p_obj.append($(`<span>‹</span>`));
        p_obj.append($(`<span>1</span>`));
        p_obj.append($(`<span>›</span>`));
        return p_obj;
    }
    
    if (selected_page == 1) {
        p_obj.append($(`<span>‹</span>`));
        p_obj.append($(`<span>1</span>`));
    } else {
        p_obj.append($(`<a href="javascript:gotoPage(${selected_page - 1});">‹</a>`));
        p_obj.append($(`<a href="javascript:gotoPage(1);">1</a>`));
    }
    start = Math.max(2, selected_page - 4);
    end = Math.min(page_count - 1, selected_page + 4);
    if (start > 2)
        p_obj.append($(`<span>...</span>`));
    for (i = start; i <= end; ++i) {
        if (i == selected_page)
            p_obj.append($(`<span>${i}</span>`));
        else
            p_obj.append($(`<a href="javascript:gotoPage(${i});">${i}</a>`));
    }
    if (end < page_count - 1)
        p_obj.append($(`<span>...</span>`));
    if (selected_page == page_count) {
        p_obj.append($(`<span>${page_count}</span>`));
        p_obj.append($(`<span>›</span>`));
    } else {
        p_obj.append($(`<a href="javascript:gotoPage(${page_count});">${page_count}</a>`));
        p_obj.append($(`<a href="javascript:gotoPage(${selected_page + 1});">›</a>`));
    }
    return p_obj;
}

function gotoPage(page) {
    query = $("#query").attr("content");
    form = $(`<form style="display: none;" action="${window.location.href}" method="POST"><input style="display: none;" name="query" type="text" value="${query}" /><input name="page" type="text" value="${page}" /></form>`);
    $("#content-outer").append(form);
    form.submit();
}

function deleteVideo(vid) {
    postJSON("/list/delete.do",
    {
        "pid": $("#playlist-id").attr("content"),
        "vid": vid,
    }, function(result){
        location.reload();
    }, function(result){
        alert(result.data);
    });
}

function moveUp(vid) {
    postJSON("/list/moveup.do",
    {
        "pid": $("#playlist-id").attr("content"),
        "vid": vid,
    }, function(result){
        location.reload();
    }, function(result){
        alert(result.data);
    });
}

function moveDown(vid) {
    postJSON("/list/movedown.do",
    {
        "pid": $("#playlist-id").attr("content"),
        "vid": vid,
    }, function(result){
        location.reload();
    }, function(result){
        alert(result.data);
    });
}

function deletePlaylist() {
    $.get("/list/{{playlist_id}}/del");
}

function setCover(vid) {
    postJSON("/list/setcover.do",
    {
        "pid": $("#playlist-id").attr("content"),
        "vid": vid,
    }, function(result){
        location.reload();
    }, function(result){
        alert(result.data);
    });
}
