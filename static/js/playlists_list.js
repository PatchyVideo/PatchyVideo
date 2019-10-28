
function search() {
    term = $("#playlist_search_term").val();
    window.location = "/lists?q=" + encodeURIComponent(term);
}

function gotoPage(page) {
    query = $("#query").attr("content");
    form = $(`<form style="display: none;" action="${window.location.href}" method="POST"><input style="display: none;" name="query" type="text" value="${query}" /><input name="page" type="text" value="${page}" /></form>`);
    $("#top-navbar").append(form);
    form.submit();
}
