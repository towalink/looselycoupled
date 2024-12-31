# -*- coding: utf-8 -*-

from collections import namedtuple
import datetime
import enum


class Priority(enum.Enum):
    HIGHEST = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    LOWEST = 5


class Metadata(namedtuple('Metadata', ('transaction', 'priority', 'source_obj', 'source_name'))):

    counter = 0  # counter for identifiers
    last_time = None  # formatted time of last transaction

    def __new__(cls, transaction=None, priority=None, source_obj=None, source_name=None):
        # Create a transaction identifier based on current UTC time and a counter
        if transaction is None:
            formatted_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
            if Metadata.last_time != formatted_time:
                Metadata.last_time = formatted_time
                Metadata.counter = 0
            transaction = formatted_time + f'-{Metadata.counter:06}'
            Metadata.counter +=1
        # Normal priority is default
        if priority is None:
            priority = Priority.NORMAL
        # Create the named tuple
        return super(Metadata, cls).__new__(cls, transaction, priority, source_obj, source_name)
