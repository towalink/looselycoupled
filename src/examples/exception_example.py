# -*- coding: utf-8 -*-

import logging

from asyncmodules import module


logger = logging.getLogger(__name__)


class ExeptionModule(module.Module):
    """Application module that raises an exception for demonstrating exception handling"""

    async def run(self, metadata):
        logger.info('run called')
        a = 1 / 0


module_class = ExeptionModule
