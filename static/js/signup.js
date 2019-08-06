
function signup() {
    username = $("#username").val();
    if (isEmpty(username)) {
        setStatus("Username cannot be empty", "red");
        return;
    }
    if (username.length < 4) {
        setStatus("Username must be at least 4 characters long", "red");
        return;
    }
    if (username.length > 32) {
        setStatus("Username length must be less than 33 characters", "red");
        return;
    }
    password1 = $("#password1").val();
    password2 = $("#password2").val();
    if (password1 != password2) {
        setStatus("Passwords mismatch", "red");
        return;
    }
    if (password2.length < 8) {
        setStatus("Password must be at least 8 characters long", "red");
        return;
    }
    if (password2.length > 64) {
        setStatus("Password length must be less than 65 characters", "red");
        return;
    }
    email = $("#email").val();
    if (!isEmpty(email)) {
        if (email.length > 128) {
            setStatus("Email length must be less than 129 characters", "red");
            return;
        }
    }
    setStatus("Signing up...");
    postJSON('/signup.do',
    {
        username: username,
        password: password1,
        email: email,
        session: $("#session").attr("content"),
    },
    function(result){
        window.location = "/login";
    },
    function(result){
        setStatus(result.data, "red");
    });
}
