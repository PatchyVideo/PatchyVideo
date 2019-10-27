
$(document).ready(function() {
    tbn_url = $("#thumbnail-url").attr("content");
    query_str = $("#query").attr("content");
    $("#search-bar-query").val(query_str);
    $("#edit-current-tags").css("display", "inline");
    $("#edit-current-tags").attr("href", "javascript:showModal();");
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
