from sqlhelper import signals

from client import clear_cache

clear_cache_exceptions = set()
def dont_clear_cache_for(table_name):
    """Used to signal that changes in a certain table don't require us to
    clear the cache.  Right now this is only the session table.
    """
    clear_cache_exceptions.add(table_name)

def handle_change(statement):
    if statement.table_name not in clear_cache_exceptions:
        clear_cache()

#signals.sql_insert.connect(handle_change)
#signals.sql_update.connect(handle_change)
#signals.sql_delete.connect(handle_change)
