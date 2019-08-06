

//////////////////////////////////////////////////////
//    Event Listeners
//////////////////////////////////////////////////////

function onCreatePlaylistButton_Click(event) {
    submitPlaylist();
}


//////////////////////////////////////////////////////
//    jQuery
//////////////////////////////////////////////////////
$(document).ready(function(){
    $("#create-playlist-button").click(onCreatePlaylistButton_Click);
    if (!isEmpty($("#pid").attr("content"))) {
        $("#create-playlist-button").text("Edit");
    }
}
);

//////////////////////////////////////////////////////
//    Functions
//////////////////////////////////////////////////////

function submitPlaylist() {
    title = $("#playlist-title").val();
    desc = $("#playlist-desc").val();
    pid = $("#pid").attr("content");
    cover = "";
    if (isEmpty(title) || isEmpty(desc)) {
        setStatus("Please fill all required fields.", "red");
        return;
    }
    postJSON("/lists/new.do",
        {
            title: title,
            desc: desc,
            cover: cover,
            pid: pid
        },
        function(result){
            pid = result.data.pid;
            window.location = "/list/" + pid;
        },
        function(result){
            alert(result.data);
        }
    );
}



