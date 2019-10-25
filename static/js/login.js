
function login() {
    username = $("#username").val();
    if (isEmpty(username)) {
        setStatus("Username cannot be empty", "red");
        return;
    }
    
    password = $("#password").val();
    if (isEmpty(password)) {
        setStatus("Password cannot be empty", "red");
        return;
    }

    redirect_url = $("#redirect_url").attr("content");

    setStatus("Logging up...");
    postJSON('/login.do',
    {
        username: username,
        password: password,
        session: $("#session").attr("content"),
    },
    function(result){
        all_queries = getUrlVars();
        if (all_queries.indexOf("redirect_url") >= 0) {
            var decoded = unescape(all_queries["redirect_url"]);
            window.location = decoded;
        } else if (!isEmpty(redirect_url)) {
            var decoded = unescape(redirect_url);
            window.location = decoded;
        } else {
            window.location = "/";
        }
    },
    function(result){
        setStatus(result.data, "red");
    });
}
