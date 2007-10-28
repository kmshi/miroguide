# sqlhelper -- SQL helper tools
# Copyright (C) 2005-2007 Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

"""sqlhelper signals."""

import logging
import traceback
from itertools import count

class Signal(object):
    def __init__(self, name, signature):
        self.name = name
        self.signature = signature
        self.listeners = {}
        self.handle_counter = count()

    def connect(self, callable, *args, **kwargs):
        handle = self.handle_counter.next()
        self.listeners[handle] = (callable, args, kwargs)
        return handle

    def disconnect(self, handle):
        del self.listeners[handle]

    def emit(self, *emitted_args):
        if len(emitted_args) != len(self.signature):
            raise ValueError('emit called with wrong number of arguments: '
                    '%s (signature: %s)' % (emitted_args, self.signature))
        for callable, args, kwargs in self.listeners.values():
            all_args = list(emitted_args) + list(args)
            try:
                callable(*all_args, **kwargs)
            except:
                logging.warn("error running callback for %s (%s, args: %s, "
                        "kwargs: %s)\n%s", self.name, callable, args, kwargs,
                        traceback.format_exc())

sql_insert = Signal('sql-insert', signature=['insert-statement'])
sql_update = Signal('sql-update', signature=['update-statement'])
sql_delete = Signal('sql-delete', signature=['delete-statement'])

record_insert = Signal('record-insert', signature=['record'])
record_update = Signal('record-update', signature=['record'])
record_delete = Signal('record-delete', signature=['record'])
