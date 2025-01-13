# -*- coding: utf-8 -*-

import asyncio
import enum
import gpiod
import logging
import threading
import time

from asyncmodules import module


logger = logging.getLogger(__name__)


class OutputState(enum.Enum):
    """Enum class for defining output states"""
    OFF = 0
    BLINK1 = 1
    BLINK2 = 2
    BLINK3 = 3
    BLINK4 = 4
    BLINK5 = 5
    ON = 6


class Output():
    """Class for keeping the state of an output"""

    def __init__(self, line_offset):
        """Instance initialization"""        
        self.line = line_offset
        self.state = OutputState.OFF
        self.value = gpiod.line.Value.INACTIVE
        self.value_new = gpiod.line.Value.INACTIVE
        self.blinktime_off = 0  # off time in milliseconds
        self.blinktime_on = 0  # on time in milliseconds
        self.blinktime_remaining = 0 #  time until next toggle in milliseconds


class Outputs(dict):
    """Class for keeping the state of all considered outputs as a dictionary of Output objects"""

    def __init__(self, line_offsets):
        """Instance initialization"""
        super().__init__()
        for line_offset in line_offsets:
            self[line_offset] = Output(line_offset)

    def set_output_value(self, line, active):
        """Sets the output value of the given line"""
        value_new = gpiod.line.Value.ACTIVE if active else gpiod.line.Value.INACTIVE
        output[line].value_new = value_new
        return value_new

    def toggle(self, line):
        """Toggles the given output and returns the new value"""
        return self.set_output_value(output[line] == gpiod.line.Value.INACTIVE)

    def get_time_wakeup(self):
        """Gets the time in milliseconds until the next wakeup for toggling"""
        time_wakeup = 1000  # wake up after 1s at latest
        for output in self.values():
            blinktime = output.blinktime_on if (output.value == gpiod.line.Value.ACTIVE) else output.blinktime_off
            if blinktime > 0:
                time_wakeup = min(time_wakeup, blinktime)
        return time_wakeup

    def elapse_time(self, ms):
        """Lets the given number of milliseconds pass and toggles outputs if needed"""
        for line, output in self.items():
            if output.blinktime_remaining > 0:
                blinktime = output.blinktime_on if (output.value == gpiod.line.Value.ACTIVE) else output.blinktime_off
                toggle = False
                if ms > output.blinktime_remaining:
                    logger.warning('Elapsed time is greater than expected next wakeup time')
                    output.blinktime_remaining = 0
                    toggle = True
                else:
                    output.blinktime_remaining -= ms  # elapse time
                    toggle = (output.blinktime_remaining <= 0)
                if toggle:
                    value_new = self.toggle(line)
                    if value_new == gpiod.line.Value.ACTIVE:
                        output.blinktime_remaining = output.blinktime_on
                    else:
                        output.blinktime_remaining = output.blinktime_off

    def get_changes_and_apply(self):
        """Gets a dictionary of changes values and makes the new values current"""
        outputs_new = dict()
        for line, output in self.items():
            if output.value != output.value_new:                
                output.value = output.value_new
                outputs_new[line] = output.value_new
        return outputs_new


class ModuleGpiod(module.Module):
    """Application module for accessing GPIOs using the gpiod library"""

    async def initialize(self, chip_name='/dev/gpiochip0', input_lines=[], output_lines=[]):
        """Module initialization"""
        # Get object for accessing the GPIO chip
        logger.info(f'Accessing GPIO chip [{chip_name}]')
        self.chip = gpiod.Chip(chip_name)
        # If just line offsets are provided (as a list), take default values for the lines
        if isinstance(input_lines, list):
            input_lines = { tuple(input_lines): gpiod.LineSettings(
                              direction=gpiod.line.Direction.INPUT,
                              edge_detection=gpiod.line.Edge.BOTH,
                              bias=gpiod.line.Bias.PULL_UP,
                              debounce_period=datetime.timedelta(milliseconds=10)
                            )
                          }
        if isinstance(output_lines, list):                          
            output_lines = { tuple(output_lines): gpiod.LineSettings(
                               direction=gpiod.line.Direction.OUTPUT,
                               output_value=gpiod.line.Value.INACTIVE
                             )
                           }
        # Initialize data structures
        self.input_lines = input_lines
        self.output_lines = output_lines
        self.outputs = Outputs(self.get_key_list(output_lines)) 
        self.event_wakeup_output = threading.Event()

    def get_key_list(self, d):
        """Returns a list of dictionary keys where the keys can be tuples or scalar values"""
        l = []
        for item in d.keys():
            if isinstance(item, tuple):
                l.extend(item)
            else:
                l.append(item)
        return l
        
    async def get_output_state(self, line):
        """Get the state of the output with the specified line offset"""
        try:
            return self.outputs[line].status
        except KeyError:
            raise ValueError(f'Output line [{line}] not handled')

    async def get_output_times(self, line):
        """Get output state as times: (0, 0) means OFF, (0, 1) means ON, else (off time in ms, on time in ms)"""
        try:
            return self.outputs[line].time_off[num], self.outputs[line].time_on[num]
        except KeyError:
            raise ValueError(f'Output line [{line}] not handled')

    async def set_output(self, line, value):
        """Set output state"""
        if line not in self.outputs.keys():
            raise ValueError(f'Output line [{line}] not handled')
        # Set times
        if value == OutputStatus.OFF:
            self.outputs[line].time_off[num] = 0
            self.outputs[line].time_on[num] = 0
        elif value == OutputStatus.BLINK1:
            pass  # ***
        elif value == OutputStatus.BLINK2:
            pass  # ***
        elif value == OutputStatus.BLINK3:
            pass  # ***
        elif value == OutputStatus.BLINK4:
            pass  # ***
        elif value == OutputStatus.BLINK5:
            pass  # ***
        elif value == OutputStatus.ON:
            self.outputs[line].time_off[num] = 0
            self.outputs[line].time_on[num] = 1
        else:
            raise ValueError('Unexpected output value')
        # Set named value
        outputs[line].state = value

    def thread_monitor_inputs(self):
        """Thread for monitoring input lines"""
        with self.chip.request_lines(consumer='asyncmodules-gpiod-in', config=self.input_lines) as request:
            while self.is_active:
                time.sleep(0.01)  # collect events for 10ms before listening (to reduce processing overhead)
                if request.wait_edge_events(timeout=1):
                    events = request.read_edge_events()
                    for event in events:
                        rising_edge = (event.event_type == event.Type.RISING_EDGE)
                        logger.info(f"Input event on line [{event.line_offset}:{event.line_seqno}]: {'rising edge' if rising_edge else 'falling edge'}")
                        self.trigger_event_threadsafe('changed_gpio_input', line=event.line_offset, line_seq={event.line_seqno}, rising_edge=rising_edge)

    def thread_manage_outputs(self):
        """Thread for controlling output lines"""
        with self.chip.request_lines(consumer='asyncmodules-gpiod-out', config=self.output_lines) as request:
            while self.is_ready:
                # Sleep until next output toggle takes place or event is fired
                start_time = time.time()
                wakeup_ms = self.outputs.get_time_wakeup()
                event_occurred = self.event_wakeup_output.wait(timeout=wakeup_ms/1000)
                if event_occurred:
                    elapsed_time = time.time() - start_time
                    wakeup_ms = elapsed_time * 1000
                self.outputs.elapse_time(wakeup_ms)
                # Apply changes output values
                outputs_new = self.outputs.get_changes_and_apply()
                if len(outputs_new):
                    request.set_values(outputs_new)
                # Clear event to be able to set it again
                self.event_wakeup_output.clear()
            # Finally switch off everything
            outputs_new = { line: gpiod.line.Value.INACTIVE for line, output in self.outputs.items() }
            request.set_values(outputs_new)

    async def run_passively(self, metadata):
        """Runs the module, process tasks/events (initiate new tasks/events only for handling them)"""
        await asyncio.to_thread(self.thread_manage_outputs)
        #coro_output = asyncio.to_thread(self.thread_manage_outputs)
        #task_output = asyncio.create_task(coro_output)
        #self.register_task(task_output)
        #await asyncio.gather(task_output, return_exceptions=True)

    async def run(self, metadata):
        """Runs the module, may actively initiate new tasks/events"""
        await asyncio.to_thread(self.thread_monitor_inputs)
        #coro_input = asyncio.to_thread(self.thread_monitor_inputs)
        #task_input = asyncio.create_task(coro_input)
        #self.register_task(task_input)
        #await asyncio.gather(task_input, return_exceptions=True)


module_class = ModuleGpiod
