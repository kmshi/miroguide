# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import time
from sqlhelper import signals

from client import set

def handle_change(statement):
    # reset the table key, so cached pages will not find the old caches
    if statement.table_name not in ('cg_session', 'cg_channel_subscription',
                                    'cg_channel_subscription_holding'):
        set('namespace', time.time())
#    set('Table:' + statement.table_name, time.time())

signals.sql_insert.connect(handle_change)
signals.sql_update.connect(handle_change)
signals.sql_delete.connect(handle_change)
