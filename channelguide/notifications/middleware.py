# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

class NotificationMiddleware(object):
    """
    NotificationMiddleware adds a add_notification(title, line) method to
    the request.  These notifications will be displayed at the top of the
    page.
    """

    def process_request(self, request):
        if hasattr(request, 'session') and 'notifications' in request.session:
            request.notifications = request.session.pop('notifications')
        else:
            request.notifications = []
        request.add_notification = (
                lambda t, l: request.notifications.append((t, l)))

    def process_response(self, request, response):
        if response.status_code != 200:
            if 'notifications' not in request.session:
                request.session['notifications'] = []
            request.session['notifications'].extend(request.notifications)
            return response
        if 'html' not in response['content-type']:
            return response
        if hasattr(request, 'notifications') and request.notifications:
            notification_bar = """    <div id="alertwrapper">
      <div class="alert">
        <div class="page">
          <div class="alertBox ">
        <ul>"""
            for (title, line) in request.notifications:
                if title is not None:
                    notification_bar += """
            <li><h2>%s</h2> %s</li>""" % (title.encode('utf8'),
                                                   line.encode('utf8'))
                else:
                    notification_bar += """
            <li>%s</li>""" % line.encode('utf8')
            notification_bar += """          </div>
        </div>
      </div>
    </div>"""
        else:
            notification_bar = ""
        response.content = response.content.replace(
                '<!-- NOTIFICATION BAR -->', notification_bar)
        return response
