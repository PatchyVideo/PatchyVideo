
function search() {
    term = $("#playlist_search_term").val();
    window.location = "/lists?q=" + encodeURIComponent(term);
}
