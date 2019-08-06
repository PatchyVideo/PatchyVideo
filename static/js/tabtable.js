
function tab_readyTabTable(tab) {
    $(".tab-content").css("display", "none");
    $(`div[page-content="${tab}"]`).css("display", "block");
    $('button[content="' + tab + '"].tab-button').addClass("active");
}

function tab_switchToTab(event, tab) {
    $(".tab-content").css("display", "none");
    $(`div[page-content="${tab}"]`).css("display", "block");
    $('.tab-button').removeClass("active");
    $('button[content="' + tab + '"].tab-button').addClass("active");
}

function tab_clearTab(tab) {
    tab_obj = $(".tab-header");
    tab_obj.html("");
}

function tab_addTab(tab, active = false, onactive = null) {
    obj = $(`<button content="${tab}" class="tab-button">${tab}</button>`);
    obj.click(function (event) {
        if(onactive) {
            onactive(tab);
        }
        tab_switchToTab(event, tab);
    });
    $(".tab-header").append(obj);
    if (active)
    tab_activeTab(tab);
}

function tab_activeTab(tab) {
    $(`button[content="${tab}"].tab-button`).click();
}

