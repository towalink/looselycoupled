from asyncmodules import module_gpiod
import datetime
import gpiod


class GpiodExample(module_gpiod.ModuleGpiod):
    """Example application module for accessing GPIOs"""

    async def initialize(self):
        """Module initialization"""
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
        await super().initialize('/dev/gpiochip0', input_lines=input_lines, output_lines=output_lines)


module_class = GpiodExample
