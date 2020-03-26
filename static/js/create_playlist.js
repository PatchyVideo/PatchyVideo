

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
    if ($("#tab-button-new").hasClass("tab-active")) {
        submitPlaylistNew();
    }
    if ($("#tab-button-existing").hasClass("tab-active")) {
        submitPlaylistExisting();
    }
}

function submitPlaylistNew() {
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

function submitPlaylistExisting() {
    url = $("#playlist-url").val();
    if (isEmpty(url)) {
        setStatus("Please fill all required fields.", "red");
        return;
    }
    postJSON("/lists/create_from_existing_playlists.do",
        {
            url: url
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
