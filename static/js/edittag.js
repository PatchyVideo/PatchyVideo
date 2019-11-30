
PAGE_SIZE = 30
USER_ID = ""

//////////////////////////////////////////////////////
//    jQuery
//////////////////////////////////////////////////////
$(document).ready(function(){
    buildTab();
    USER_ID = $("#uid").attr("content");
}
);

function refreshTable(category) {
    alert("refresh "+category);
}

function removeTag(tag, category) {
    var ask = confirm("Are you sure you are going to delete " + tag);
    if (ask) {
        status_obj = $(`p[meta-category="${category}"]`);
        postJSON("/tags/remove_tag.do",
        {
            "tag": tag
        }, function (result){
            gotoPage(category, 1);
        }, function (result){
            status_obj.css("display", "block");
            status_obj.css("color", "red");
            status_obj.text(result.data.reason);
        });
    }
}

function addTag(category, tag) {
    status_obj = $(`p[meta-category="${category}"]`);
    if (tag.length > 0) {
        postJSON("/tags/add_tag.do",
        {
            "tag": tag,
            "category": category
        }, function (result){
            gotoPage(category, 1);
        }, function (result){
            status_obj.css("display", "block");
            status_obj.css("color", "red");
            status_obj.text(result.data.reason);
        });
    } else {
        status_obj.css("display", "block");
        status_obj.css("color", "red");
        status_obj.text("Tag can not be empty");
    }
}

function add_textcomplete(element) {
    element.textcomplete([
        {
            id: 'tags',
            match: /\b([\w][\w][\w_\-\!']*(_\([\w'\-_\!]+\)?)?)$/,
            search: function (term, callback) {
                $.getJSON( "https://patchyvideo.com/autocomplete/?q=" + term, function( data ) {
                    data = $.map(data, function(ele) {
                        ele['term'] = term;
                        ele['color'] = getCategoryColor(ele['category']);
                        return ele;
                    });
                    callback(data);
                });
            },
            template: function (value) {
                suffix = value.src.substring(value.term.length);
                highlighted_term = `<b>${value.term}</b>${suffix}`;
                if (isEmpty(value.dst)) {
                    return `<span style="color: ${value.color};"><span style="margin-right: 6em;">${highlighted_term}</span></span><span style="float:right;">${value.count}</span>`;
                } else {
                    return `<span style="color: ${value.color};"><span>${highlighted_term}</span>-><span style="margin-right: 6em;">${value.dst}</span></span><span style="float:right;">${value.count}</span>`;
                }
            },
            replace: function (value) {
                if (isEmpty(value.dst)) {
                    return value.src;
                } else {
                    return value.dst;
                }
            },
            index: 1
        }
    ],
    {
        onKeydown: function (e, commands) {
            if (e.ctrlKey && e.keyCode === 74) { // CTRL-J
                return commands.KEY_ENTER;
            }
        },
        placement: "matchinput"
    });
}

function buildToolBar(category, tag_count, display_count) {
    layout = $(`<div class="tag-tool-bar"></div>`);
    info_obj = $(`<p>Showing ${display_count} out of ${tag_count} tags</p>`);
    add_tag_input_obj = $(`<input type="text" meta-category="${category}" placeholder="Add tag to ${category}"></input>`);
    add_textcomplete(add_tag_input_obj);
    status_obj = $(`<p meta-category="${category}" id="status-bar" style="margin: 3px; margin-left: 0px; display: none;"></p>`);
    add_tag_btn_obj = $(`<button>Add Tag</button>`);
    add_tag_btn_obj.click(function (event){
        addTag(category, $(`input[meta-category="${category}"]`).val());
    });
    layout.append(info_obj);
    layout.append(add_tag_input_obj);
    layout.append(add_tag_btn_obj);
    layout.append(status_obj);
    return layout;
}

function gotoPage(category, page) {
    div_obj = $(`div[page-content="${category}"]`);
    if (div_obj.length == 0)
        return;
    div_obj.html('');
    postJSON("/tags/query_tags.do", {
        "page": page,
        "page_size": PAGE_SIZE,
        "category": category
    }, function (result) {
        table_obj = $(`<table content="${category}"></table>`);
        toolbar_obj = buildToolBar(category, result.data.count, result.data.tags.length);
        tr = $(`<tr><th class="col-1">Count</th><th>Tag</th></tr>`);
        table_obj.append(tr);
        result.data.tags.forEach(element => {
            if (element.meta.created_by.$oid == USER_ID) {
                if (isEmpty(element.dst))
                {
                    if (isEmpty(element.languages))
                    {
                        tr = $(`<tr class="table-content"><td class="col-1">${element.count}</td><td><a href="/search?query=${element.tag}">${element.tag}</a>
                        <a class="tag-operation" href="javascript:removeTag('${element.tag}', '${category}');">Remove</a>
                        </tr>`);
                    }
                    else
                    {
                        var new_element = `<tr class="table-content"><td class="col-1">${element.count}</td><td><a href="/search?query=${element.tag}">${element.tag}</a>`;
                        new_element += `<span class="other-language">`;
                        for (var lang_key in element.languages)
                        {
                            new_element += `${lang_key}:<a href="/search?query=${element.languages[lang_key]}">${element.languages[lang_key]}</a> `;
                        }
                        new_element += `</span>`;
                        new_element += `</tr>`;
                        tr = $(new_element);
                    }
                } else {
                    if (!isEmpty(element.type) && element.type == "language")
                    {
                        return;
                    }
                    tr = $(`<tr class="table-content"><td class="col-1">-</td><td>
                    ${element.tag}<span> -> </span>
                    <a href="/search?query=${element.dst}">${element.dst}</a>
                    <a class="tag-operation" href="javascript:removeTag('${element.tag}', '${category}');">Remove</a>
                    </tr>`);
                }
            } else {
                tr = $(`<tr class="table-content"><td class="col-1">${element.count}</td><td><a href="/search?query=${element.tag}">${element.tag}</a></td></tr>`);
            }
            table_obj.append(tr);
        });
        p_obj = buildPageSelector(category, page, result.data.page_count);
        div_obj.append(toolbar_obj);
        div_obj.append(table_obj);
        div_obj.append(p_obj);
    });
}

function downloadTags(category) {
    obj = $(`div[page-content="${category}"]`);
    if (obj.length == 0) {
        div_obj = $(`<div page-content="${category}" class="tab-content"></div>`);
        $("#primary").append(div_obj);
        gotoPage(category, 1);
    }
}

function showPage(category, page) {

}

function buildPageSelector(category, selected_page, page_count) {
    if (selected_page > page_count || page_count < 1)
        return null;
    p_obj = $(`<p class="page-selector"></p>`);
    if (page_count == 1) {
        p_obj.append($(`<span>‹</span>`));
        p_obj.append($(`<span>1</span>`));
        p_obj.append($(`<span>›</span>`));
        return p_obj;
    }
    
    if (selected_page == 1) {
        p_obj.append($(`<span>‹</span>`));
        p_obj.append($(`<span>1</span>`));
    } else {
        p_obj.append($(`<a href="javascript:gotoPage('${category}', ${selected_page - 1});">‹</a>`));
        p_obj.append($(`<a href="javascript:gotoPage('${category}', 1);">1</a>`));
    }
    start = Math.max(2, selected_page - 4);
    end = Math.min(page_count - 1, selected_page + 4);
    if (start > 2)
        p_obj.append($(`<span>...</span>`));
    for (i = start; i <= end; ++i) {
        if (i == selected_page)
            p_obj.append($(`<span>${i}</span>`));
        else
            p_obj.append($(`<a href="javascript:gotoPage('${category}', ${i});">${i}</a>`));
    }
    if (end < page_count - 1)
        p_obj.append($(`<span>...</span>`));
    if (selected_page == page_count) {
        p_obj.append($(`<span>${page_count}</span>`));
        p_obj.append($(`<span>›</span>`));
    } else {
        p_obj.append($(`<a href="javascript:gotoPage('${category}', ${page_count});">${page_count}</a>`));
        p_obj.append($(`<a href="javascript:gotoPage('${category}', ${selected_page + 1});">›</a>`));
    }
    return p_obj;
}

function buildTab() {
    postJSON("/tags/query_categories.do",
    {}, function (result) {
        first = true;
        result.data.categories.forEach(element => {
            tab_addTab(element.name, first, downloadTags);
            first = false;
        });
    }
    );
}


