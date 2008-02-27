# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from sqlhelper.orm import columns, Table

task_time = Table('cg_task_time', 
        columns.String('name', 255, primary_key=True),
        columns.DateTime('last_run_time'))
