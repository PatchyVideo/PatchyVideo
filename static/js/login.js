
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
    
    setStatus("Logging up...");
    postJSON('/login.do',
    {
        username: username,
        password: password,
        session: $("#session").attr("content"),
    },
    function(result){
        window.location = "/";
    },
    function(result){
        setStatus(result.data, "red");
    });
}
