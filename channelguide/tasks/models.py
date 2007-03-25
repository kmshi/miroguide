from datetime import datetime

from sqlalchemy import mapper

from channelguide.tasks import tables

class TaskTime(object):
    def __init__(self, name):
        self.name = name
        self.last_run_time = datetime.now()

    def update_last_run_time(self):
        self.last_run_time = datetime.now()

mapper(TaskTime, tables.task_time)
