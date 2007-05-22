from datetime import datetime

from sqlhelper.orm import Record

from channelguide.tasks import tables

class TaskTime(Record):
    table = tables.task_time

    def __init__(self, name):
        self.name = name
        self.last_run_time = datetime.now()

    def update_last_run_time(self):
        self.last_run_time = datetime.now()
