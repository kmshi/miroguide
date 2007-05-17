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
