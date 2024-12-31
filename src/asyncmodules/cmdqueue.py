# -*- coding: utf-8 -*-

import asyncio
from collections import namedtuple

from .metadata import Metadata


class CmdQueue(asyncio.PriorityQueue):
    """Child class of an async priority queue with adapted queue items"""

    QueueItem = namedtuple('QueueItem', ['target', 'metadata', 'kwargs'])

    async def put(self, target=None, metadata=None, kwargs=None):
        """Put an item with the provided attribute values into the queue"""
        if metadata is None:
            metadata = Metadata()
        await super().put((metadata.priority, CmdQueue.QueueItem(target, metadata, kwargs )))
