import logging
import traceback
from datetime import datetime
from models import TaskTime

class Task(object):
    def __init__(self, func, name, interval):
        self.func = func
        self.name = name
        self.interval = interval

    def should_run(self, connection):
        try:
            time = TaskTime.get(connection, self.name)
        except LookupError:
            return True
        return (datetime.now() - time.last_run_time) > self.interval

    def run(self, connection):
        try:
            self.func()
        except:
            logging.warn("\nError running scheduled task: %s\n\n%s\n" % 
                    (self.name, traceback.format_exc()))
        else:
            self.update_time(connection)

    def update_time(self, connection):
        try:
            time = TaskTime.get(connection, self.name)
        except LookupError:
            time = TaskTime(self.name)
        else:
            time.update_last_run_time()
        time.save(connection)
        connection.commit()

class TaskRegistry(object):
    def __init__(self):
        self.tasks = []

    def add_task(self, func, name, interval):
        self.tasks.append(Task(func, name, interval))

    def run_tasks(self, connection):
        for task in self.tasks:
            if task.should_run(connection):
                task.run(connection)

global_registry = TaskRegistry()
def add_task(func, name, interval):
    global_registry.add_task(func, name, interval)

def run_tasks(connection):
    global_registry.run_tasks(connection)
