function infiniteLoad(data, textStatus) {
    content = $('#content', data);
    results = content.find('#searchResults > li')
    $('#searchResults').append(results);
    nextpage = content.find('#next-page');
    if (!nextpage.length) {
        $('#next-page').remove();
    } else {
        $('#next-page').attr('href', nextpage.attr('href')).show();
    }
    checkScroll.loading = false;
    hideLoadIndicator();
}

function checkScroll() {
    nextpage = $('#next-page');
    if (!nextpage.length) return;
    doc = $(document);
    distance = doc.height() - doc.scrollTop() - $(window).height();
    if (distance < nextpage.height() && !checkScroll.loading) {
        checkScroll.loading = true;
        nextpage.hide();
        showLoadIndicator(true);
        $.get(nextpage.attr('href'), infiniteLoad);
    }
}

checkScroll.loading = false;

$(document).scroll(checkScroll);