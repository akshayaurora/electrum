from kivy.utils import get_color_from_hex
from kivy.clock import Clock

import threading
import queue
from typing import (NamedTuple, Callable, Optional)

def address_colors(wallet, addr):
    """
    Chooses the appropriate text color and background color to 
    mark receiving, change and billing addresses.

    Returns: color, background_color
    """

    # modified colors (textcolor, background_color) from electrum/gui/qt/util.py
    GREEN = ("#000000", "#8af296")
    YELLOW = ("#000000", "#ffff00")
    BLUE = ("#000000", "#8cb3f2")
    DEFAULT = ('#ffffff', '#4c4c4c')

    colors = DEFAULT
    if wallet.is_mine(addr):
        colors = YELLOW if wallet.is_change(addr) else GREEN
    elif wallet.is_billing_address(addr):
        colors = BLUE
    return (get_color_from_hex(color) for color in colors)


class TaskThread(threading.Thread):
    '''Thread that runs background tasks.  Callbacks are guaranteed
    to happen in the UI Thread.'''

    class Task(NamedTuple):
        task: Callable
        cb_success: Optional[Callable]
        cb_done: Optional[Callable]
        cb_error: Optional[Callable]


    def __init__(self, parent, on_error=None):
        super(TaskThread, self).__init__()
        self.on_error = on_error
        self.tasks = queue.Queue()
        self.start()

    def add(self, task, on_success=None, on_done=None, on_error=None):
        on_error = on_error or self.on_error
        self.tasks.put(TaskThread.Task(task, on_success, on_done, on_error))

    def run(self):
        while True:
            task = self.tasks.get()  # type: TaskThread.Task
            if not task:
                break
            try:
                result = task.task()
                self.on_done(result, task.cb_done, task.cb_success)
            except BaseException:
                import sys
                self.on_done(sys.exc_info(), task.cb_done, task.cb_error)

    def on_done(self, result, cb_done, cb_result):
        # This runs in the parent's thread.
        if cb_done:
            Clock.schedule_once(lambda dt: cb_done())
        if cb_result:
            Clock.schedule_once(lambda dt: cb_result(result))

    def stop(self):
        self.tasks.put(None)
