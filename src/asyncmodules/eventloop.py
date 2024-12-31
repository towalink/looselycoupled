# -*- coding: utf-8 -*-
 
import asyncio
import logging

from . import cmdqueue


logger = logging.getLogger(__name__)


class EventLoop():
    """Implements an synchronous event loop for managing and executing tasks"""
    _queue = None  # queue for keeping tasks for later execution

    def __init__(self, process_item_func, queue_empty_func=None):
        """Initialization"""
        self._process_item_func = process_item_func
        self._queue_empty_func = queue_empty_func
        self._queue = cmdqueue.CmdQueue()

    async def process_task(self):
        """Gets and processes a single task from the queue"""
        # Get a single item
        priority, item = await self._queue.get()
        logger.debug('Got item [[item]] from queue')
        # Process a single item
        await self._process_item_func(item)
        self._queue.task_done()
        # Trigger event if nothing more is to be done
        if self._queue.empty() :
            if self._queue_empty_func is not None:
                if await self._queue_empty_func():
                    self._running = False        
                    return False
        return True

    async def process_queue(self, forever=False):
        """Processes items from the queue until it is empty"""
        while forever or not self._queue.empty():
            result = await self.process_task()
            if not result:
                forever = False

    async def run_eventloop(self):
        """Prepare and run the main loop"""
        self._running = True
        while self._running:
            await self.process_queue(forever=True)

    @property
    def queue(self):        
        return self._queue
