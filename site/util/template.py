"""Helper classes for the templates"""

from urllib import urlencode

class Pager(object):
    """Handles splitting a large group of results into separate pages."""

    def __init__(self, items_per_page, select, request):
        """Construct a Pager.  Arguments:

        items_per_page -- number of items per page
        select -- SelectResults object to select from
        request -- current request
        """

        try:
            self.current_page = int(request.GET.get('page', 1))
        except ValueError:
            raise Http404
        self.items_per_page = items_per_page
        # Need to clear order_by before getting a count
        self.total_items = select.order_by(None).count()
        self.calc_range()
        self.items = select.offset(self.start_item-1).limit(self.items_per_page)
        self.items = self.items.list()
        self.links = PageLinks(self.current_page, self.total_pages, request)

    def calc_range(self):
        self.start_item = (self.current_page-1)* self.items_per_page + 1
        self.end_item = self.start_item + self.items_per_page-1
        self.start_item = max(1, self.start_item)
        self.end_item = min(self.total_items, self.end_item)
        self.total_pages = ((self.total_items + self.items_per_page-1) /
                self.items_per_page)

class PageLinks(object):
    LINKS_BEFORE_CURRENT = 5
    LINKS_AFTER_CURRENT = 5

    def __init__(self, current, total, request):
        self.current = current
        self.last = total
        self.link_prefix = request.path[1:]
        self.request_params = request.GET.copy()
        self.before_current = []
        self.after_current = []
        self.before_current_pos = current
        self.after_current_pos = current

        self.extend_before_curent(self.LINKS_BEFORE_CURRENT)
        self.extend_after_current(self.LINKS_AFTER_CURRENT)
        # we could call self.adjust_left() here, but that causes the links to
        # jump around when they are clicked, and page is towards the end.  I
        # (ben) think it's niecer not to do that.
        self.adjust_right()
        self.make_start_links()
        self.make_end_links()
        self.make_next_link()
    
    def extend_before_curent(self, count):
        self.before_current_pos -= count
        links = self.make_links(self.before_current_pos, count)
        self.before_current = links + self.before_current

    def extend_after_current(self, count):
        links = self.make_links(self.after_current_pos+1, count)
        self.after_current_pos += count
        self.after_current = self.after_current + links

    def adjust_left(self):
        unused = self.LINKS_AFTER_CURRENT - len(self.after_current)
        if unused > 0:
            self.extend_before_curent(unused)

    def adjust_right(self):
        unused = self.LINKS_BEFORE_CURRENT - len(self.before_current)
        if unused > 0:
            self.extend_after_current(unused)

    def make_start_links(self):
        if self.before_current_pos <= 1:
            self.start = []
        else:
            self.start = [self.make_link(1)]
            # shorten by 2 to make room for the start link and the ellipsis
            self.before_current = self.before_current[2:]

    def make_end_links(self):
        if self.after_current_pos >= self.last:
            self.end = []
        else:
            # shorten by 2 to make room for the end link and the ellipsis
            self.end = [self.make_link(self.last)]
            self.after_current = self.after_current[:-2]

    def make_next_link(self):
        if self.current < self.last:
            self.next = self.make_link(self.current+1)
        else:
            self.next = ''

    def make_url(self, page_number):
        self.request_params['page'] = page_number
        return '%s?%s' % (self.link_prefix, urlencode(self.request_params))

    def make_link(self, page_number):
        return {'url': self.make_url(page_number), 'number': page_number}

    def make_links(self, start, count):
        end = min(start + count, self.last + 1)
        start = max(start, 1)
        return [self.make_link(n) for n in xrange(start, end)]

class ViewSelect(object):
    """Handles the links at the top right of the popular/category/tag etc.
    pages.  This class is intended to be subclassed, with subclasses providing
    the following attributes:

    base_url -- the begining part of the URL that we link to.
    view_choices -- The possible choices, this is a list of (choice, label)
      pairs.  For example:

      [ ('date', _("Most Recent")),
        ('alphabetical', _("A-Z")),
        ...
      ]
    """

    def __init__(self, request):
        self.current_choice = request.GET.get('view', self.view_choices[0][0])

    def view_links(self):
        for choice, label in self.view_choices:
            yield {
                'url': "%s?view=%s" % (self.base_url, choice),
                'is_current': (self.current_choice == choice),
                'label': label
            }
