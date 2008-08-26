function infiniteCallback(data, textStatus) {
    content = $('#content', data);
    results = content.find('#searchResults > li')
    $('#searchResults').append(results);
    results.find('ul.rating').rating();
    location.href = '#' + results.find('a').attr('name');
    nextpage = content.find('#next-page');
    if (!nextpage.length) {
        $('#next-page').remove();
    } else {
        $('#next-page').attr('href', nextpage.attr('href')).show();
    }
    checkScroll.loading = false;
    hideLoadIndicator();
    checkHash();
}

function checkScroll() {
    nextpage = $('#next-page');
    if (!nextpage.length) return;
    doc = $(document);
    distance = doc.height() - doc.scrollTop() - $(window).height();
    if (distance < nextpage.height() && !checkScroll.loading)
        infiniteLoad();
}

function infiniteLoad() {
    nextpage = $('#next-page');
    if (checkScroll.loading)
        return;
    checkScroll.loading = true;
    nextpage.hide();
    showLoadIndicator(true);
    $.get(nextpage.attr('href'), infiniteCallback);
}

function checkHash() {
    if (!checkHash.hash) {
        checkHash.hash = hash = location.hash.substring(1);
    } else {
        hash = checkHash.hash;
    }
    if (!$('a[name=' + hash + ']').length) {
        nextpage = $('#next-page');
        if (!nextpage.length)
            return;
        infiniteLoad();
    }
}
checkScroll.loading = false;

$(document).scroll(checkScroll).ready(checkHash);