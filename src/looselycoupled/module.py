# -*- coding: utf-8 -*-

import asyncio
import enum
import inspect
import logging
import threading

from . import configuration
from . import eventloop
from .metadata import Metadata


logger = logging.getLogger(__name__)
cfg = configuration.get_config()


class States(enum.Enum):
    """Define the states of a module"""
    inactive = 1  # not ready for sending and receiving event notifications
    passive = 2  # ready for receiving event notifications, not allowed to send yet
    active = 3  # ready for receiving and sending event notifications


class Module():
    """Application module (abstract class)"""

    def __init__(self, name, function_references):
        """Instance initialization"""
        self._name = name
        self._function_references = function_references
        self._task_passive = None
        self._task_active = None
        self._state = States.inactive
        self.event_no_longer_active = threading.Event()
        self.event_no_longer_passive = threading.Event()

    def get_method(self, methodname):
        """Returns a reference to the method with the given name"""
        try:
            method = getattr(self, methodname)
        except AttributeError:
            method = None
        return method

    async def call_method(self, methodname, log_unknown=True, **kwargs):
        """Calles the method of this object instance with the given name and arguments; optionally logs if method unknown"""
        if (method := self.get_method(methodname)) is not None:
            if inspect.iscoroutinefunction(method):
                return await method(**kwargs)
            else:
                return method(**kwargs)
        else:
            if log_unknown:
                logger.error(f'Called method [{methodname}] unknown in module [{self.name}]')

    async def exec_task(self, task, **kwargs):
        """Helper method for synchronous execution of a task"""
        if not 'metadata' in kwargs:
            kwargs['metadata'] = Metadata(source_obj=self, source_name=self.name)
        return await self._function_references.exec_task(task, **kwargs)

    def exec_task_threadsafe(self, task, **kwargs):
        """Helper method for synchronous execution of a task"""
        if not 'metadata' in kwargs:
            kwargs['metadata'] = Metadata(source_obj=self, source_name=self._name)
        return self._function_references.exec_task_threadsafe(task, **kwargs)

    async def enqueue_task(self, task, **kwargs):
        """Helper method to queue a task for asynchronous execution"""
        if not self.is_active:
            logger.warn(f'Module not active when enqueuing task [{task}]')
        if '.' not in task:
            task = self._name + '.' + task
        if not 'metadata' in kwargs:
            kwargs['metadata'] = Metadata(source_obj=self, source_name=self._name)
        return await self._function_references.enqueue_task(task, **kwargs)

    def enqueue_task_threadsafe(self, task, **kwargs):
        """Helper method to queue a task for asynchronous execution"""
        if not self.is_active:
            logger.warn(f'Module not active when enqueuing task [{task}]')
        if '.' not in task:
            task = self._name + '.' + task
        if not 'metadata' in kwargs:
            kwargs['metadata'] = Metadata(source_obj=self, source_name=self._name)
        return self._function_references.enqueue_task_threadsafe(task, **kwargs)

    async def trigger_event(self, event=None, **kwargs):
        """Helper method to trigger an event asynchronously"""
        if not self.is_active:
            logger.warn(f'Module not active when triggering event [{event}]')
        if event is None:
            event = self._name + '_event'
        if not 'metadata' in kwargs:
            kwargs['metadata'] = Metadata(source_obj=self, source_name=self._name)
        await self._function_references.trigger_event(event, **kwargs)

    def trigger_event_threadsafe(self, event=None, **kwargs):
        """Helper method to trigger an event asynchronously"""
        if not self.is_active:
            logger.warn(f'Module not active when triggering event [{event}]')
        if event is None:
            event = self._name + '_event'
        if not 'metadata' in kwargs:
            kwargs['metadata'] = Metadata(source_obj=self, source_name=self._name)
        self._function_references.trigger_event_threadsafe(event, **kwargs)

    def register_task(self, task, name):
        """Register a task for exception handling and management"""
        return self._function_references.register_task(task, name)

    def get_config(self, itemname, default=None):
        """Return a configuration item"""
        return cfg.get_item(self._name + '.' + itemname, default)

    async def run_passively(self, metadata):
        """Runs the module, process tasks/events (initiate new tasks/events only for handling them)"""
        pass

    async def _run_passively(self):
        """Runs the module, process tasks/events (initiate new tasks/events only for handling them); internal method"""
        self.state = States.passive
        logger.debug('Run module (passively)')
        metadata = Metadata(source_obj=self, source_name=self._name)
        await self.run_passively(metadata)

    async def run(self, metadata):
        """Runs the module, may actively initiate new tasks/events"""
        pass

    async def _run(self):
        """Runs the module, may actively initiate new tasks/events; internal method"""
        if self.state == States.passive:
            self.state = States.active
        else:
            logger.warning(f'Attempted to activate module [{self._name}] that was not in passive state before')
        logger.debug('Run module')
        metadata = Metadata(source_obj=self, source_name=self._name)
        await self.run(metadata=metadata)

    async def initialize(self):
        """Called at module startup for initialization purposes"""
        pass

    async def startup(self, metadata):
        """Initialization of the module (get config)"""
        await self.initialize()
        self.event_no_longer_passive.clear()        
        # asyncio.create_task(self._run_passively()) with exception handling:        
        self._task_passive = await self._function_references.schedule_method(self, '_run_passively')

    async def activate(self, metadata):
        """Go into active state"""
        self.event_no_longer_active.clear()        
        # asyncio.create_task(self._run()) with exception handling:
        self._task_active = await self._function_references.schedule_method(self, '_run')

    async def deactivate(self, metadata):
        """Go back into passive state (trigger stopping of "active" coroutine)"""
        if self.state == States.active:
            self.state = States.passive
            self.event_no_longer_active.set()

    async def initiate_shutdown(self, metadata):
        """Shutdown the module (prepare/initiate shutdown; trigger stopping of "passive" coroutine)"""
        # Latest now, the "active" coroutine must have finished
        if self._task_active is not None:
            asyncio.gather(self._task_active, return_exceptions=True)
            self._task_active = None
        # We're going into "inactive" state now
        self.state = States.inactive
        self.event_no_longer_passive.set()

    async def finalize_shutdown(self, metadata):
        """Shutdown the module (cleanup activities)"""
        assert self._task_active is None
        # Latest now, the "passive" coroutine must have finished
        if self._task_passive is not None:
            asyncio.gather(self._task_passive, return_exceptions=True)
            self._task_passive = None

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, newstate):
        self._state = newstate
        logger.debug(f'New state [{newstate}] for module [{self._name}]')

    @property
    def is_ready(self):
        return (self.state == States.passive) or (self.state == States.active)

    @property
    def is_active(self):
        return self.state == States.active
