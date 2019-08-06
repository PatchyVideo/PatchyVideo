
function changepass() {
    password1 = $("#password1").val();
    password2 = $("#password2").val();
    password3 = $("#password3").val();
    if (password3 != password2) {
        setStatus("Passwords mismatch", "red");
        return;
    }
    if (password3.length < 8) {
        setStatus("Password must be at least 8 characters long", "red");
        return;
    }
    if (password3.length > 64) {
        setStatus("Password length must be less than 65 characters", "red");
        return;
    }
    setStatus("Changing password...");
    postJSON('/user/changepass.do',
    {
        old_pass: password1,
        new_pass: password3
    },
    function(result){
        setStatus("Password changed");
    },
    function(result){
        setStatus(result.data, "red");
    });
}

function changedesc() {
    desc = $("#desc").val();
    if (desc.length > 2000) {
        setStatus("Description length must be less than 2000 characters", "red");
        return;
    }
    setStatus("Updating description...");
    postJSON('/user/changedesc.do',
    {
        desc: desc,
    },
    function(result){
        setStatus("Description updated");
    },
    function(result){
        setStatus(result.data, "red");
    });
}
