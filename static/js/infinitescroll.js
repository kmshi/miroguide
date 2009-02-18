function infiniteCallback(data, textStatus) {
    newBody = $("<div/>").append(
        RegExp("<body[^\>]*>([\\s\\w\\W]*)\<\/body\>", "g").exec(data)[1]);
    results = $('.scrolling', newBody);
    // XXX this doesn't handle the case where there are more shows than feeds
    for (i=0; i < 2; i++) {
        items = results.eq(i).children('li:gt(0)');
        items.find('form.rating').rating();
        items.find('.rating').height(25);
        if (typeof setUpItem == 'function')
            items.find('div.details').each(setUpItem);
        $('.scrolling').eq(i).append(items);
    }
    $('ul.paginator, ul.paginator2').replaceWith(
        $('ul.paginator, ul.paginator2', newBody));
    checkScroll.loading = false;
    add_corners();
    hideLoadIndicator();
}

function checkScroll() {
    first = $('ul.scrolling li:last');
    nextpage = $('ul.paginator li.selected + li, ul.paginator2 li.selected + li');
    if (!nextpage.length) return;
    doc = $(document);
    distance = doc.height() - doc.scrollTop() - $(window).height();
    if (distance < nextpage.height() + (first.height() * 5) &&
        !checkScroll.loading)
        infiniteLoad();
    as = $('.scrolling li > a[name]');
    i = 0;
    while (i < as.length && as[i].offsetTop < $(window).scrollTop()) {
        i++;}
    if (i > 1) {
        location.href = '#pg' + as.eq(i - 1).attr('name');
    } else if (location.hash) {
        location.href = '#pg' + as.eq(0).attr('name');
    }
}

function infiniteLoad() {
    if (checkScroll.loading)
        return;
    nextpage = $('ul.paginator2 li.selected + li, ul.paginator li.selected + li');
    checkScroll.loading = true;
    showLoadIndicator(true);
    $.get(nextpage.find('a').attr('href'), infiniteCallback);
}

function checkHash() {
    if (!location.hash) return;
    hash = location.hash.substring(3);
    if (isNaN(parseInt(hash)))
        return;
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

$(window).scroll(checkScroll);
checkHash();