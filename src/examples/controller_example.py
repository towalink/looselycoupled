# -*- coding: utf-8 -*-

import logging

from looselycoupled import module


logger = logging.getLogger(__name__)


class ControllerExampleModule(module.Module):
    """Example Controller module"""

    async def on_changed_gpio_input(self, metadata, line, line_name, line_seq, rising_edge):
        logger.info(f'on_changed_gpio_input called for line [{line_name}:{line}:{line_seq}], rising edge [{rising_edge}]')

    async def on_webpage_trigger(self, metadata):
        """Receives broadcast that gets sent when button 'Trigger Action' is pushed on webpage"""
        logger.info('on_webpage_trigger called')
        await self.enqueue_task('gpiod_example.modify_output_states')

    async def run(self, metadata):
        logger.info('run called')


module_class = ControllerExampleModule
