# -*- coding: utf-8 -*-

import logging

from asyncmodules import module


logger = logging.getLogger(__name__)


class SimpleExampleModule(module.Module):
    """Example Application module"""

    def myfunc(self, param):
        logger.info('myfunc called')

    async def myfunc_async(self, param):
        logger.info('myfunc_async called')

    async def run(self, metadata):
        logger.info('run called')
        # Call a method in local module asynchronously, i.e. we put it into the queue and do not wait for the result
        await self.enqueue_task('myfunc', param='Hello')
        await self.enqueue_task('myfunc_async', param='World')
        # Call a method in another module synchronously
        pos = await self.exec_task('cherrypy_example.add_log_entry', metadata=metadata, text='This line was synchronously added by the module "simple_example"')
        logger.info(f'Synchronous call to cherrypy_example.add_line yields result [{pos}]')
        # Call a method in another module asynchronously, i.e. we put it into the queue and do not wait for the result
        await self.enqueue_task('cherrypy_example.add_log_entry', text='This line was asynchronously added by the module "simple_example"')
        # Trigger an event to all modules listening for it by implementing a corresponding "on_<event>" method
        await self.trigger_event('my_simple_example_event', param='This line was asynchronously added by the module "simple_example" by triggering an event')


module_class = SimpleExampleModule
