"""Utility functions."""

def ensure_list(obj):
    if hasattr(obj, '__iter__'):
        return obj
    else:
        return [obj]
