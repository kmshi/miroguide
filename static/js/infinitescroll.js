function infiniteCallback(data, textStatus) {
    content = $('#content', data);
    results = content.find('#searchResults > li')
    $('#searchResults').append(results);
    results.find('ul.rating').rating();
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
    if (distance < nextpage.height() && !checkScroll.loading)
        infiniteLoad();
    as = $('a[name]');
    i = 0;
    while (i < as.length && as[i].offsetTop < doc.scrollTop())
        i++;
    if (i > 1) {
        location.href = '#pg' + as.eq(i - 1).attr('name');
    } else if (location.hash) {
        location.href = '#pg' + as.eq(0).attr('name');
    }
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
    if (!location.hash) return;
    hash = location.hash.substring(3);
    try {
        parseInt(hash)
    } catch (e) {
        return;
    }
    if (!$('a[name=' + hash + ']').length) {
        args = location.search;
        if (!args) {
            args = '?page=' + hash;
        } else if (args.indexOf('page=') != -1) {
            args = args.replace(/page=[^&]*/, 'page=' + hash);
        } else {
            args = args + '&page=' + hash;
        }
        location.href = location.protocol + '//' + location.host +
            location.pathname + args;
    }
}
checkScroll.loading = false;

$(document).scroll(checkScroll);
checkHash();