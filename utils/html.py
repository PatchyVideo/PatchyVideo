
def getInnerText(list_of_elements) :
    txt = ''
    for ele in list_of_elements :
        if isinstance(ele, str) :
            txt += ele
        else :
            txt += ele.text
    return txt

def buildPageSelector(selected_page, page_count, page_url_callback) :
    if selected_page > page_count or page_count < 1 :
        return ''
    ans = ''
    if page_count == 1 :
        return '<span>‹</span><span>1</span><span>›</span>'
    if selected_page == 1 :
        ans += '<span>‹</span><span>1</span>'
    else :
        ans += '<a href="%s">‹</a>' % page_url_callback(selected_page - 1)
        ans += '<a href="%s">1</a>' % page_url_callback(1)

    start = max(2, selected_page - 4)
    end = min(page_count - 1, selected_page + 4)

    if start > 2 :
        ans += '<span>...</span>'
    
    for i in range(start, end + 1) :
        if i == selected_page :
            ans += '<span>%d</span>' % i
        else :
            ans += '<a href="%s">%d</a>' % (page_url_callback(i), i)
    
    if end < page_count - 1 :
        ans += '<span>...</span>'
    if selected_page == page_count :
        ans += '<span>%d</span>' % page_count
        ans += '<span>›</span>'
    else :
        ans += '<a href="%s">%d</a>' % (page_url_callback(page_count), page_count)
        ans += '<a href="%s">›</a>' % page_url_callback(selected_page + 1)
    return ans
    
