# -*- coding: utf-8 -*-

import asyncio
import logging
from asyncmodules import module


logger = logging.getLogger(__name__)


class ModuleThreaded(module.Module):
    """Extension of application module to support running in separate threads"""

    def run_as_thread(self, method_name):
        """Runs the specified method in a separate thread and registers it as task"""
        try:
            method = getattr(self, method_name)
        except AttributeError:
            method = None
        if method is not None:
            logger.debug(f'Starting separate thread for executing [{method_name}]...')
            coro_output = asyncio.to_thread(method)
            task_output = asyncio.create_task(coro_output)
            self.register_task(task_output)

    async def run_passively(self, metadata):
        """Runs the module, process tasks/events (initiate new tasks/events only for handling them)"""
        self.run_as_thread('thread_run_passively')

    async def run(self, metadata):
        """Runs the module, may actively initiate new tasks/events"""
        self.run_as_thread('thread_run')
