
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
	var ask = confirm("你确定要删除" + tag);
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
		status_obj.text("标签不能为空");
	}
}

function add_textcomplete(element) {
	element.textcomplete([
		{
			id: 'tags',
			match: function(text) {
				var i = text.length;
				while (i--) {
					if (text.charAt(i) == ' ' ||
						text.charAt(i) == '\t' ||
						text.charAt(i) == '\n' ||
						text.charAt(i) == '\v' ||
						text.charAt(i) == '\f' ||
						text.charAt(i) == '\r') {
						return i + 1;
					}
				}
				return 0;
			},
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

function buildToolBar(category, tag_count, display_count, order) {
	layout = $(`<div class="tag-tool-bar"></div>`);
	header_obj = $(`<div></div>`);
	info_obj = $(`<p style="display: inline;">显示${display_count}/${tag_count}个标签</p>`);
	add_tag_input_obj = $(`<input type="text" meta-category="${category}" placeholder="向${category}类别添加标签"></input>`);
	add_textcomplete(add_tag_input_obj);
	status_obj = $(`<p meta-category="${category}" id="status-bar" style="margin: 3px; margin-left: 0px; display: none;"></p>`);
	order_obj = $(`
		<select class="select-tag-order" id="select-order-${category}" onchange="javascript:gotoPage('${category}', 1);">
		<option value="latest" selected="">最新</option>
		<option value="oldest">最老</option>
		<option value="count">数量</option>
		</select>
		`);
	if (isEmpty(order)) {
		order = 'latest';
	}
	order_obj.val(order);
	add_tag_btn_obj = $(`<button>添加</button>`);
	add_tag_btn_obj.click(function (event){
		addTag(category, $(`input[meta-category="${category}"]`).val());
	});
	header_obj.append(info_obj);
	header_obj.append(order_obj);
	layout.append(header_obj);
	layout.append(add_tag_input_obj);
	layout.append(add_tag_btn_obj);
	layout.append(status_obj);
	return layout;
}

function expandLanguageEdit(obj) {
	tag = $(obj).attr("data-tag");
	row = $(`[data-tag="${tag}"]`);
	visible = $("span.unselectable", row).text() == "-";
	if (visible) {
		$("span.other-language", row).css("display", "");
		$("div.edit-language-div", row).css("display", "none");
		$("span.unselectable", row).text("+");
	} else {
		$("span.other-language", row).css("display", "none");
		$("div.edit-language-div", row).css("display", "block");
		$("span.unselectable", row).text("-");
	}
}

function onAliasChanged(obj) {
	parent = $(obj).parent();
	new_alias = $(obj).val().trim();
	old_alias = $(obj).attr("data-alias");
	if (new_alias !== old_alias) {
		$("button.multilanguage-tag-save", parent).css("visibility", "visible");
	} else {
		$("button.multilanguage-tag-save", parent).css("visibility", "hidden");
	}
}

function saveLanguageAlias(obj) {
	parent = $(obj).parent();
	input_obj = $("input.multilanguage-tag-textbox", parent);
	button_obj = $("button.multilanguage-tag-save", parent);
	new_alias = input_obj.val().trim();
	old_alias = input_obj.attr("data-alias");
	language = parent.attr("data-language");
	console.log(`change "${old_alias}" to "${new_alias}" for lang ${language}`); // TODO: ....
	postJSON("/tags/rename_tag.do",
    {
		"tag": old_alias,
		"new_tag": new_alias
    }, function(result){
        input_obj.attr("data-alias", new_alias);
		button_obj.css("visibility", "hidden");
		td = parent.parent().parent();
		other_language_obj = $("span.other-language", td);
		other_language_item_obj = $(`span[data-lang=${language}]`, other_language_obj);
		other_language_item_a_obj = $("a", other_language_item_obj);
		other_language_item_a_obj.attr("href", `/search?query=${new_alias}`);
		other_language_item_a_obj.text(`${new_alias}`);
    }, function(result){
        alert(result.data.reason);
    });
	
}

function addLanguageAlias(obj) {
	parent = $(obj).parent();
	input_obj = $("input.add-multilanguage-textbox", parent);
	alias_text = input_obj.val().trim();
	select_obj = $("select", parent);
	language = select_obj.val();
	tag = parent.attr("data-tag");
	console.log(`adding "${alias_text}" to "${tag}" for lang ${language}`); // TODO: ....
	postJSON("/tags/add_tag_language.do",
    {
		"alias": alias_text,
		"dst_tag": tag,
		"language": language
    }, function(result){
		edit_language_div_obj = parent.parent();
		lang_row_obj = $(`<div data-language="${language}">
		<span>${_LANGUAGE_MAP[language]}</span>
		<input oninput="onAliasChanged(this);" data-alias="${alias_text}" data-tag="${tag}" class="multilanguage-tag-textbox" value="${alias_text}" />
		<button onclick="saveLanguageAlias(this);" data-tag="${tag}" class="multilanguage-tag-save">保存</button>
		</div>
		`);
		option_to_remove = $(`option[value=${language}]`, select_obj);
		option_to_remove.remove();
		input_obj.val("");
		edit_language_div_obj.append(lang_row_obj);
		td = edit_language_div_obj.parent();

		other_language_obj = $("span.other-language", td);
		new_other_language_obj = $(`<span data-lang="${language}">${_LANGUAGE_MAP[language]}:<a href="/search?query=${alias_text}">${alias_text}</a></span>`);
		other_language_obj.append(new_other_language_obj);
	}, function(result){
        alert(result.data.reason);
    });
}

function buildAddLanguageRow(tag, languages) {
	var html = `<div class="add-language-div" data-tag="${tag}">`;
	var remaining_languages = [];
	if (isEmpty(languages)) {
		for (lang_key in _LANGUAGE_MAP) {
			remaining_languages.push(lang_key);
		}
	} else {
		for (lang_key in _LANGUAGE_MAP) {
			if (!(lang_key in languages)) {
				remaining_languages.push(lang_key);
			}
		}
	}
	if (remaining_languages.length > 0) {
		html += `<select>`;
		remaining_languages.forEach(function(lang) {
			html += `<option value="${lang}">${_LANGUAGE_MAP[lang]}</option>`;
		});
		html += `</select>`;
		html += `<input class="add-multilanguage-textbox" />`;
		html += `<button onclick="addLanguageAlias(this);" class="multilanguage-tag-save" style="visibility: visible;">添加</button>`;
	}
	html += `</div>`;
	return html;
}

function gotoPage(category, page) {
	div_obj = $(`div[page-content="${category}"]`);
	if (div_obj.length == 0)
		return;
	order = $(`#select-order-${category}`).val();
	div_obj.html('');
	postJSON("/tags/query_tags.do", {
		"page": page,
		"page_size": PAGE_SIZE,
		"category": category,
		"order": order
	}, function (result) {
		table_obj = $(`<table content="${category}"></table>`);
		toolbar_obj = buildToolBar(category, result.data.count, result.data.tags.length, order);
		tr = $(`<tr><th class="col-1">数量</th><th></th><th>标签</th></tr>`);
		table_obj.append(tr);
		result.data.tags.forEach(element => {
			var expandObj = `<td class="col-2" onclick="javascript:expandLanguageEdit(this);" data-tag="${element.tag}"><span class="unselectable">+</span></td>`;
			if (isEmpty(element.dst))
			{
				var new_element = `
				<tr class="table-content" data-tag="${element.tag}">
					<td class="col-1">${element.count}</td>
					${expandObj}
					<td>
						<div>
							<a href="/search?query=${element.tag}">${element.tag}</a>
							<a class="tag-operation" href='javascript:removeTag("${element.tag}", "${category}");'>删除</a>
					`;
				new_element += `<span class="other-language">`;
				if (!isEmpty(element.languages))
				{
					for (var lang_key in element.languages)
					{
						new_element += `<span data-lang="${lang_key}">${_LANGUAGE_MAP[lang_key]}:<a href="/search?query=${element.languages[lang_key]}">${element.languages[lang_key]}</a></span>`;
					}
				}
				new_element += `</span>`;
				new_element += `</div>`;
				new_element += `<div class="edit-language-div">`;
				new_element += buildAddLanguageRow(element.tag, element.languages);
				for (var lang_key in element.languages)
				{
					new_element += `<div data-language="${lang_key}">
					<span>${_LANGUAGE_MAP[lang_key]}</span>
					<input oninput="onAliasChanged(this);" data-alias="${element.languages[lang_key]}" data-tag="${element.tag}" class="multilanguage-tag-textbox" value="${element.languages[lang_key]}" />
					<button onclick="saveLanguageAlias(this);" data-tag="${element.tag}" class="multilanguage-tag-save">保存</button>
					</div>
					`;
				}
				new_element += `</div>`;
				new_element += `</td>`;
				new_element += `</tr>`;
				tr = $(new_element);
			} else {
				tr = $(`
				<tr class="table-content" data-tag="${element.tag}">
					<td class="col-1">-</td>
					<td class="col-2"></td>
					<td>${element.tag}<span> -> </span>
						<a href="/search?query=${element.dst}">${element.dst}</a>
					</td>
					<a class="tag-operation" href='javascript:removeTag("${element.tag}", "${category}");'>删除</a>
				</tr>`);
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


