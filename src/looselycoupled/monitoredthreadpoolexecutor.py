import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import threading


logger = logging.getLogger(__name__)


class MonitoredThreadPoolExecutor(ThreadPoolExecutor):
    """ A subclass of ThreadPoolExecutor that track active worker threads"""

    def __init__(self, *args, **kwargs):
        """Object initialization"""
        super().__init__(*args, **kwargs)
        self._max_workers = kwargs.get('max_workers', 0)
        self._current_workers = 0
        self._lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        """Increase worker count and handle submission as usual"""
        with self._lock:
            self._current_workers += 1
            if (self._max_workers > 0) and (self._current_workers >= self._max_workers):
                logger.error(f'Max workers [{self._max_workers}] reached, increase the number of workers! Attempted to run [{fn}]')
        result = super().submit(fn, *args, **kwargs)

        def callback(_):
            """Callback to decrease the worker count once the thread is done"""
            with self._lock:
                self._current_workers -= 1

        result.add_done_callback(callback)
        return result
