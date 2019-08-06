
$(document).ready(function() {
    tbn_url = $("#thumbnail-url").attr("content");
    query_str = $("#query").attr("content");
    $("#search-bar-query").val(query_str);
    $("#edit-current-tags").css("display", "inline");
    $("#edit-current-tags").attr("href", "javascript:showModal();");
    tags = $("#tags").attr("content");
    edit_str = "";
    
    tags.split(/ /).forEach(element => {
        edit_str += element + "\n";
    });

    $("#edit-tags-area").text(edit_str);

    $(".close").click(function(){
        hideModal();
    });
    $(".ok").click(function(){
        doEdit();
    });
});

function doEdit() {
    tags = $("#edit-tags-area").val().split(/\r?\n/).filter(function(i){return i})
    $(".ok").text("Please wait");
    postJSON("/videos/edittags.do",
    {
        "video_id": $("#video-id").attr("content"),
        "tags": tags,
    }, function(result){
        hideModal();
        location.reload();
    }, function(result){
        alert(result.data);
        $(".ok").text("Confirm");
    });
}

function showModal() {
    $(".modal").css("display", "block");
}

function hideModal() {
    $(".modal").css("display", "none");
}

function breaklink() {
    postJSON("/videos/breaklink.do",
    {
        "video_id": $("#video-id").attr("content"),
    }, function(result)
    {
        location.reload();
    });
}
