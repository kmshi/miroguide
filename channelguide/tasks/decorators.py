from datetime import timedelta
import registry

def run_every(minutes=0, hours=0, days=0, weeks=0):
    def decorator(func):
        task_name = func.__name__
        interval = timedelta(minutes=minutes, hours=hours, days=days,
                weeks=weeks)
        registry.add_task(func, task_name, interval)
        return func
    return decorator

def run_every_hour(func):
    return run_every(hours=1)(func)

def run_every_day(func):
    return run_every(days=1)(func)

def run_every_week(func):
    return run_every(weeks=1)(func)
