# -*- coding: utf-8 -*-

import logging

from looselycoupled import module


logger = logging.getLogger(__name__)


class ControllerExampleModule(module.Module):
    """Example Controller module"""

    async def on_changed_gpio_input(self, metadata, line, rising_edge):
        logger.info('on_changed_gpio_input called for line [{line}], rising edge [{rising_edge}]')

    async def on_webpage_trigger(self):
        """Receives broadcast that gets sent when button 'Trigger Action' is pushed on webpage"""
        logger.info('on_webpage_trigger called')
        await self.enqueue_task('gpiod_example.modify_output_states')

    async def run(self, metadata):
        logger.info('run called')


module_class = ControllerExampleModule
