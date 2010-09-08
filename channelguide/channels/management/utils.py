import socket
import threading
import Queue

from channelguide import util

from channelguide.channels.models import Channel


print_stuff = True

def all_channel_iterator(task_description, **kwargs):
    """Helper method to iterate over all channels.  It will yield each channel
    in order.
    """
    if 'approved' in kwargs:
        approved = kwargs.pop('approved')
    else:
        approved = False
    if approved:
        channels = Channel.objects.approved()
    else:
        channels = Channel.objects.all()
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, channels.count())
        pprinter.print_status()
    for channel in channels:
        yield channel
        if print_stuff:
            pprinter.iteration_done()
    if print_stuff:
        pprinter.loop_done()

def spawn_threads_for_channels(task_description, callback, thread_count):
    """Works with update_items and download_thumbnails to manage worker
    threads that update the individual channels.
    """
    queue = Queue.Queue()
    for channel in Channel.objects.all():
        queue.put(channel)
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, queue.qsize())
        pprinter.print_status()
    class Worker(threading.Thread):
        def run(self):
            while True:
                try:
                    channel = queue.get(block=False)
                except Queue.Empty:
                    break
                callback(channel)
                if print_stuff:
                    pprinter.iteration_done()
    threads = [Worker() for x in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if print_stuff:
        pprinter.loop_done()

def set_short_socket_timeout():
    socket.setdefaulttimeout(10) # makes update_items not take forever
