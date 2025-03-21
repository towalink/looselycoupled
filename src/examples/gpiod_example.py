# -*- coding: utf-8 -*-

import datetime
import logging

try:
    import gpiod
except ModuleNotFoundError:
    from looselycoupled import mock_gpiod as gpiod

from looselycoupled import module_gpiod


logger = logging.getLogger(__name__)


class GpiodExample(module_gpiod.ModuleGpiod):
    """Example application module for accessing GPIOs"""

    async def initialize(self):
        """Module initialization"""
        # Provide GPIOD Line Settings
        input_lines = { 22: gpiod.LineSettings(
                                direction=gpiod.line.Direction.INPUT,
                                edge_detection=gpiod.line.Edge.BOTH,
                                bias=gpiod.line.Bias.PULL_UP,
                                debounce_period=datetime.timedelta(milliseconds=10)
                            )
                      }
        output_lines = { (4, 17, 27): gpiod.LineSettings(
                                          direction=gpiod.line.Direction.OUTPUT,
                                          output_value=gpiod.line.Value.INACTIVE
                                      )
                       }
        # Assign human readable alias names for the lines
        line_names = {
                    4 : 'Output4_NothingSpecial',
                    17 : 'Output17_ForBlinking',
                    22 : 'Input22_ForTestingPurposes',
                    27 : 'Output27_NothingSpecial'
                }
        # Let the parent method do the work
        await super().initialize('/dev/gpiochip0', input_lines=input_lines, output_lines=output_lines, line_names=line_names)

    async def modify_output_states(self, metadata):
        """Changes outputs for demonstration purposes"""
        # Line 4
        await self.set_output_state(4, module_gpiod.OutputState.ON)
        # Line 17
        state = await self.get_output_state(17)
        if state == module_gpiod.OutputState.OFF:
            state_new = module_gpiod.OutputState.ON
        elif state == module_gpiod.OutputState.ON:
            state_new = module_gpiod.OutputState.BLINK_VERYSLOW
        elif state == module_gpiod.OutputState.BLINK_VERYSLOW:
            state_new = module_gpiod.OutputState.BLINK_SLOW
        elif state == module_gpiod.OutputState.BLINK_SLOW:
            state_new = module_gpiod.OutputState.BLINK
        elif state == module_gpiod.OutputState.BLINK:
            state_new = module_gpiod.OutputState.BLINK_FAST
        elif state == module_gpiod.OutputState.BLINK_FAST:
            state_new = module_gpiod.OutputState.OFF
        else:
            logger.error('Unknown output state')
        await self.set_output_state('Output17_ForBlinking', state_new)
        logger.info(f'Setting output 17 to state [{state_new}]')
        # Line 27
        await self.toggle_output_state(27)



module_class = GpiodExample
