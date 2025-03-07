# -*- coding: utf-8 -*-

import asyncio
from collections import namedtuple, OrderedDict
import datetime
import importlib
import logging
import signal
import sys
import threading
import traceback

from . import eventloop
from .metadata import Metadata


logger = logging.getLogger(__name__)


class ModuleManager(object):
    """Class to handle modules"""
    _modules = OrderedDict()  # Dictionary of module data

    def __init__(self, appmodules, exception_path=None):
        """Initialization"""
        self._exception_path = exception_path
        self._modules = OrderedDict()
        self._thread_reference = threading.current_thread() 
        self._running_tasks = dict()
        self._finished_tasks = dict()
        self._exit = False
        self.register_modules(appmodules)

    def create_metadata(self):
        """Create a new metadata object"""
        return Metadata(source_obj=self, source_name='modulemanager')

    def register_module(self, modulename, moduleunit):
        """Register a module"""
        module = moduleunit.module_class
        module_obj = module(modulename, self.function_references)
        self._modules[modulename] = module_obj

    def register_modules(self, appmodules):
        """Register all modules in the provided dictionary"""
        if appmodules is not None:
            for modulename, moduleunit in appmodules.items():
                self.register_module(modulename, moduleunit)

    def is_ready_module(self, modulename):
        """Checks whether a module is available and ready"""
        if not (modulename in self._modules):
            return False
        return self._modules[modulename].is_ready

    def get_running_task_names(self):
        """Returns a list of names of all running tasks"""
        return self._running_tasks.values()

    def task_done_callback(self, task):
        """React on a finished coroutine"""
        self._finished_tasks[task] = self._running_tasks[task]
        del self._running_tasks[task]        
        try:
            task.result()
        except Exception as e:
            # Print exceptions and log to file
            logger.critical(f'Exception occured: [{str(e)}]')
            logger.exception('Exception info:')  # just error but prints traceback
            if self._exception_path is not None:
                with open(self._exception_path, 'a') as handle:
                    handle.write(datetime.datetime.now().isoformat(sep=' '))
                    handle.write('\n')
                    traceback.print_exc(file=handle)
                    handle.write('\n')                

    def register_task(self, task, name='[unnamed]'):
        """Register a task for exception handling and management"""
        self._running_tasks[task] = name
        task.add_done_callback(self.task_done_callback)

    async def schedule_method(self, module, methodname, log_unknown=True, **kwargs):
        """Call a method asynchronously as a separate asyncio coroutine"""
        methodinfo = f'{module.name}.{methodname}({str(kwargs)})'

        async def wait_for_free_task_slot():
            wait_condition = lambda: len(self._running_tasks) > 3 * len(self._modules)  # adapt rule if needed
            if wait_condition():
                logger.info(f'Waiting for free slot before starting the next task [{methodinfo}]')
                sleeptime = 0.001  # start with one millisecond
                while wait_condition():
                    await asyncio.sleep(sleeptime)
                    if sleeptime < 1:
                        sleeptime *= 2  # double sleeptime in each iteration
                    else:
                        logger.warning(f'Starting the next task [{methodinfo}] after a long wait; check reasons for long running tasks')
                        break  # don't wait indefinitely
                logger.debug('Waiting done')

        if module.get_method(methodname) is not None:
            logger.debug(f'Scheduling method call asynchronously [{methodinfo}]')
            await wait_for_free_task_slot()
            task = asyncio.create_task(module.call_method(methodname, log_unknown, **kwargs))
            self.register_task(task, name=methodinfo)
            return task
        else:
            if log_unknown:
                logger.error(f'Called method [{methodname}] unknown in module [{module.name}]')
            return None

    async def exec_task_internal(self, target, metadata, asynchronous=False, **kwargs):
        """Execute the specified task (target specifies the method to be called) synchronously with the given arguments"""
        logger.debug(f'Executing task [{target}({str(kwargs)})]')
        modulename, _, methodname = target.partition('.')
        if not self.is_ready_module(modulename):
            logger.error(f'Method module [{target}] is in an inactive state or unknown module was tried to be called')
            return None
        module = self._modules.get(modulename)
        if module is None:
            logger.error(f'Unknown module [{modulename}] for task [{target}]')
        else:
            kwargs['metadata'] = metadata
            if asynchronous:
                await self.schedule_method(module, methodname, **kwargs)
                return False            
            else:
                return await module.call_method(methodname, **kwargs)

    def exec_task_threadsafe(self, target, metadata, asynchronous=False, **kwargs):
        """Execute a task while ensuring that no other task is running in parallel"""
        logger.debug(f'Executing task [{target}({str(kwargs)})] in a threadsafe manner')
        task = asyncio.run_coroutine_threadsafe(self.exec_task_internal(target, metadata, asynchronous, **kwargs), self.loop)
        result = task.result()  # this will block until the result is available
        return result

    async def exec_task(self, target, metadata, asynchronous=False, **kwargs):
        """Execute the specified task (target specifies the method to be called) synchronously with the given arguments, getting a lock if needed"""
        if self._thread_reference == threading.current_thread():
            return await self.exec_task_internal(target, metadata, asynchronous, **kwargs)
        else:
            return self.exec_task_threadsafe(target, metadata, asynchronous, **kwargs)

    async def enqueue_task_internal(self, target, metadata, **kwargs):
        """Enqueue the provided task for asynchronous execution"""
        logger.debug(f'Enqueuing task [{target}({str(kwargs)})]')
        await self._eventloop.queue.put(target=target, metadata=metadata, kwargs=kwargs)

    def enqueue_task_threadsafe(self, target, metadata, **kwargs):
        """Enqueue the provided task for asynchronous execution"""
        logger.debug(f'Enqueuing task [{target}({str(kwargs)})] in a threadsafe manner')
        asyncio.run_coroutine_threadsafe(self.enqueue_task_internal(target=target, metadata=metadata, **kwargs), self.loop)

    async def enqueue_task(self, target, metadata, **kwargs):
        """Enqueue the provided task for asynchronous execution"""
        if self._thread_reference == threading.current_thread():
            return await self.enqueue_task_internal(target=target, metadata=metadata, **kwargs)
        else:
            return self.enqueue_task_threadsafe(target=target, metadata=metadata, **kwargs)

    async def trigger_event_internal(self, event, metadata, **kwargs):
        """Enqueue the provided event for asynchronous event handling"""
        target = 'on_' + event
        logger.debug(f'Triggering event target [{target}({str(kwargs)})]')        
        await self._eventloop.queue.put(target=target, metadata=metadata, kwargs=kwargs)

    def trigger_event_threadsafe(self, event, metadata, **kwargs):
        """Enqueue the provided event for asynchronous event handling"""
        logger.debug(f'Triggering event [{event}({str(kwargs)})] in a threadsafe manner')
        asyncio.run_coroutine_threadsafe(self.trigger_event_internal(event=event, metadata=metadata, **kwargs), self.loop)

    async def trigger_event(self, event, metadata, **kwargs):
        """Enqueue the provided event for asynchronous event handling"""
        if self._thread_reference == threading.current_thread():
            return await self.trigger_event_internal(event=event, metadata=metadata, **kwargs)
        else:
            return self.trigger_event_threadsafe(event=event, metadata=metadata, **kwargs)

    async def broadcast_event_internal(self, event, metadata, asynchronous=True, **kwargs):
        """Immediately send the specified event with the given arguments to all participants with a matching event handler"""
        logger.debug(f'Broadcasting event [{event}({str(kwargs)})')
        for modulename, module_obj in self._modules.items():
            if metadata.source_obj != module_obj:  # split horizon, don't provide event to source
                kwargs['metadata'] = metadata
                if asynchronous:
                    await self.schedule_method(module_obj, event, log_unknown=False, **kwargs)
                else:
                    await module_obj.call_method(event, log_unknown=False, **kwargs)
        if event == 'on_exit':
            logger.info('Shutting down after on_exit event notification...')
            self._exit = True
            await self.broadcast_event_internal('deactivate', metadata=self.create_metadata(), asynchronous=False)
            await self.broadcast_event_internal('initiate_shutdown', metadata=self.create_metadata(), asynchronous=False)
            await self.broadcast_event_internal('finalize_shutdown', metadata=self.create_metadata(), asynchronous=False)

    def broadcast_event_threadsafe(self, event, metadata, asynchronous=True, **kwargs):
        """Handle an event while ensuring that no other task is running in parallel"""
        logger.debug(f'Broadcasting event [{event}({str(kwargs)})] in a threadsafe manner')
        asyncio.run_coroutine_threadsafe(self.broadcast_event_internal(event=event, metadata=metadata, asynchronous=asynchronous, **kwargs), self.loop)

    async def broadcast_event(self, event, metadata, asynchronous=True, **kwargs):
        """Handle an event, getting a lock if needed"""
        if self._thread_reference == threading.current_thread():
            return await self.broadcast_event_internal(event=event, metadata=metadata, asynchronous=asynchronous, **kwargs)
        else:
            return self.broadcast_event_threadsafe(event=event, metadata=metadata, asynchronous=asynchronous, **kwargs)

    async def process_item(self, item):
        """Process an item from the event queue"""
        if '.' in item.target:
            await self.exec_task(target=item.target, metadata=item.metadata, asynchronous=True, **(item.kwargs))            
        else:
            await self.broadcast_event(event=item.target, metadata=item.metadata, **(item.kwargs))

    async def gather_finished_tasks(self):
        """Gather all finished tasks"""
        await asyncio.gather(*(self._finished_tasks.keys()), return_exceptions=True)
        self._finished_tasks.clear()

    async def queue_empty(self):
        """React on empty event queue"""
        await self.gather_finished_tasks()  # clean up finished stuff
        await self.broadcast_event('becoming_idle', metadata=self.create_metadata())
        if self._exit:
            await asyncio.gather(*(self._running_tasks.keys()), return_exceptions=True)
            if not len(self._running_tasks):
                return True
        return False

    async def maintask(self):
        """Main task handling the lifecycle"""
        # Create and start event loop
        self._eventloop = eventloop.EventLoop(self.process_item, self.queue_empty)
        task_eventloop = asyncio.create_task(self._eventloop.run_eventloop())
        # Initialize modules
        await self.broadcast_event_internal('startup', metadata=self.create_metadata(), asynchronous=False)
        logger.debug(f'Startup done; application-wide scheduled tasks: {self.get_running_task_names()}')
        await asyncio.sleep(0)  # let other tasks run first (not really needed but makes sense)
        await self.broadcast_event_internal('activate', metadata=self.create_metadata(), asynchronous=False)
        logger.debug(f'Activation done; application-wide scheduled tasks: {self.get_running_task_names()}')
        await asyncio.sleep(0)  # let other tasks run first (not really needed but makes sense)
        # Wait for the event loop to terminate
        await task_eventloop
        logger.debug(f'Event loop ended')
        # Final clean-up
        await self.gather_finished_tasks()

    def on_signal(self, signum, handler):
        """React on a received operating system signal"""
        raise(KeyboardInterrupt)  # react on signal like as with a keyboard interrupt

    def run(self):
        """Run the program"""
        # Register signal handler
        signal.signal(signal.SIGINT, self.on_signal)
        signal.signal(signal.SIGTERM, self.on_signal)
        # Run asyncio loop
        loop = self.loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            maintask = loop.create_task(self.maintask())
            done = False
            while not done:
                try:
                    loop.run_until_complete(maintask)
                    done = True
                except KeyboardInterrupt:
                    logger.info('Keyboard interrupt received. Exiting...')
                    # Shutdown by broadcasting shutdown event
                    task = loop.create_task(self.trigger_event(event='exit', metadata=self.create_metadata()))
                    self.register_task(task, name='triggering of exit event')
            logger.debug('Asyncio event-loop complete')
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                logger.warning(f'Cancelling task [{task}]')
                task.cancel()
            loop.stop()
            logger.debug('Asyncio event-loop stopped')            
        finally:
            loop.close()

    @property
    def function_references(self):
        """Return reference to functions for calling from external modules"""
        FunctionReferences = namedtuple('FunctionReferences', [
            'trigger_event', 'trigger_event_threadsafe', 
            'enqueue_task', 'enqueue_task_threadsafe',
            'exec_task', 'exec_task_threadsafe',
            'broadcast_event', 
            'schedule_method', 
            'register_task'
        ])
        return FunctionReferences(
            self.trigger_event, self.trigger_event_threadsafe, 
            self.enqueue_task, self.enqueue_task_threadsafe,
            self.exec_task, self.exec_task_threadsafe,
            self.broadcast_event, 
            self.schedule_method, 
            self.register_task
        )
