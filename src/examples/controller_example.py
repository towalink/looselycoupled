# -*- coding: utf-8 -*-

import logging

from asyncmodules import module


logger = logging.getLogger(__name__)


class ControllerExampleModule(module.Module):
    """Example Controller module"""

    async def on_changed_gpio_input(self, metadata, line, rising_edge):
        logger.info('on_changed_gpio_input called for line [{line}], rising edge [{rising_edge}]')

    async def run(self, metadata):
        logger.info('run called')


module_class = ControllerExampleModule
