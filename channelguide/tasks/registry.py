import logging
import traceback
from datetime import datetime
from models import TaskTime

class Task(object):
    def __init__(self, func, name, interval):
        self.func = func
        self.name = name
        self.interval = interval

    def should_run(self, db_session):
        time = db_session.get(TaskTime, self.name)
        return (time is None or 
                (datetime.now() - time.last_run_time) > self.interval)

    def run(self, db_session):
        try:
            self.func()
        except:
            logging.warn("\nError running scheduled task: %s\n\n%s\n" % 
                    (self.name, traceback.format_exc()))
        else:
            self.update_time(db_session)

    def update_time(self, db_session):
        time = db_session.get(TaskTime, self.name)
        if time is None:
            time = TaskTime(self.name)
            db_session.save(time)
        else:
            time.update_last_run_time()
        db_session.flush()

class TaskRegistry(object):
    def __init__(self):
        self.tasks = []

    def add_task(self, func, name, interval):
        self.tasks.append(Task(func, name, interval))

    def run_tasks(self, db_session):
        for task in self.tasks:
            if task.should_run(db_session):
                task.run(db_session)

global_registry = TaskRegistry()
def add_task(func, name, interval):
    global_registry.add_task(func, name, interval)

def run_tasks(db_session):
    global_registry.run_tasks(db_session)
