# -*- coding: utf-8 -*-

import asyncio
import enum
import logging
import threading
import time

try:
    import gpiod
except ModuleNotFoundError:
    from looselycoupled import mock_gpiod as gpiod

from looselycoupled import module_threaded


logger = logging.getLogger(__name__)


class OutputState(enum.Enum):
    """Enum class for defining output states"""
    OFF = 0
    BLINK_VERYSLOW = 1
    BLINK_SLOW = 2
    BLINK = 3
    BLINK_FAST = 4
    BLINK_VERYFAST = 5
    ON = 6


class Output():
    """Class for keeping the state of an output"""

    def __init__(self, line_offset):
        """Instance initialization"""        
        self.line = line_offset  # line identifier (BCM pin number)
        self.state = OutputState.OFF  # high-level state: Off/Blink*/On
        self.value = gpiod.line.Value.INACTIVE  # current output value
        self.value_new = gpiod.line.Value.INACTIVE  # new output value to be provisioned

    def set_state(self, state_new):
        """Sets the output state for the given line"""
        if self.state != state_new:
            self.state = state_new
            if state_new == OutputState.OFF:
                self.set_output_value(False)
            elif state_new == OutputState.ON:
                self.set_output_value(True)
            else:  # blink
                # Change something immediately to indicate state change to the user
                self.toggle_value()

    def set_output_value(self, active):
        """Sets the output value of the given line"""
        value_new = gpiod.line.Value.ACTIVE if active else gpiod.line.Value.INACTIVE
        self.value_new = value_new
        return value_new

    def toggle_value(self):
        """Toggles the given output and returns the new value"""
        value_new = (self.value == gpiod.line.Value.INACTIVE)
        return self.set_output_value(value_new)


class Outputs(dict):
    """Class for keeping the state of all considered outputs as a dictionary of Output objects"""

    def __init__(self, line_offsets):
        """Instance initialization"""
        super().__init__()
        for line_offset in line_offsets:
            self[line_offset] = Output(line_offset)

    def get_changes_and_apply(self):
        """Makes the new values current and returns a dictionary of changes values"""
        outputs_new = dict()
        for line, output in self.items():
            if output.value != output.value_new:                
                output.value = output.value_new
                outputs_new[line] = output.value_new
        return outputs_new


class BlinkRhythm():
    """Class for keeping infos about a blink rhythm"""
    time_off = 0  # off time in milliseconds
    time_on = 0  # on time in milliseconds
    time_remaining = 0 #  time until next toggle in milliseconds

    def __init__(self, time_off, time_on):
        """Object initialization"""
        self.active = False
        self.time_off = time_off
        self.time_on = time_on
        self.time_remaining = time_off


class BlinkRhythms(dict):
    """Class for managing synchronized blinking rhythms"""

    def __init__(self):
        """Instance initialization"""
        super().__init__()
        self[OutputState.BLINK_VERYSLOW] = BlinkRhythm(2000, 2000)
        self[OutputState.BLINK_SLOW] = BlinkRhythm(1600, 1600)
        self[OutputState.BLINK] = BlinkRhythm(1200, 1200)
        self[OutputState.BLINK_FAST] = BlinkRhythm(800, 800)
        self[OutputState.BLINK_VERYFAST] = BlinkRhythm(400, 400)

    def get_time_wakeup(self):
        """Gets the time in milliseconds until the next wakeup for toggling"""
        time_wakeup = 1000  # wake up after 1s at latest
        for rhythm in self.values():
            blinktime = rhythm.time_remaining
            if blinktime > 0:
                time_wakeup = min(time_wakeup, blinktime)
        return time_wakeup

    def elapse_time(self, ms, outputs):
        """Lets the given number of milliseconds pass and toggles outputs if needed"""
        for id, rhythm in self.items():
            if rhythm.time_remaining > 0:
                blinktime = rhythm.time_on if rhythm.active else rhythm.time_off
                toggle = False
                if ms > rhythm.time_remaining:
                    logger.warning(f'Elapsed time [{ms} ms] is greater than expected next wakeup time [{rhythm.time_remaining} ms]')
                    rhythm.time_remaining = 0
                    toggle = True
                else:
                    rhythm.time_remaining -= ms  # elapse time
                    toggle = (rhythm.time_remaining <= 0)
                if toggle:
                    rhythm.active = not rhythm.active
                    for line, output in outputs.items():
                        if output.state == id:
                            outputs[line].set_output_value(rhythm.active)
                    rhythm.time_remaining = rhythm.time_on if rhythm.active else rhythm.time_off


class ModuleGpiod(module_threaded.ModuleThreaded):
    """Application module for accessing GPIOs using the gpiod library"""

    async def initialize(self, chip_name='/dev/gpiochip0', input_lines=[], output_lines=[], line_names=[]):
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
        self.blinkrhythms = BlinkRhythms()
        self.input_lines = input_lines
        self.output_lines = output_lines
        self.line_names = line_names
        self.outputs = Outputs(self.get_key_list(output_lines)) 
        self.event_wakeup_output = threading.Event()

    def get_key_list(self, d):
        """Returns a list of dictionary keys (the keys can be tuples or scalar values)"""
        l = []
        for item in d.keys():
            if isinstance(item, tuple):
                l.extend(item)
            else:
                l.append(item)
        return l

    def get_line_byname(self, line):
        """Gets line number by line number or line name"""
        if isinstance(line, str):
            try:
                # Get key of "line_names" dictionary by value
                line = list(self.line_names.keys())[list(self.line_names.values()).index(line)]
            except ValueError:
                raise ValueError(f'Line name [{line}] unknown')    
        return line

    async def get_output_state(self, line):
        """Get the state of the output with the specified line offset"""
        line = self.get_line_byname(line)
        try:
            return self.outputs[line].state
        except KeyError:
            raise ValueError(f'Output line [{line}] not handled')

    async def set_output_state(self, metadata, line, state_new):
        """Set output state"""
        line = self.get_line_byname(line)
        if line not in self.outputs.keys():
            raise ValueError(f'Output line [{line}] not handled')
        self.outputs[line].set_state(state_new)
        self.event_wakeup_output.set()  # notify the output change

    async def toggle_output_state(self, metadata, line):
        """Toggles the state of the output with the specified line offset"""
        line = self.get_line_byname(line)
        state = await self.get_output_state(line)
        state_new = OutputState.ON if (state == OutputState.OFF) else OutputState.OFF
        await self.set_output_state(line, state_new)

    def thread_run_passively(self):
        """Thread for controlling output lines"""
        with self.chip.request_lines(consumer='looselycoupled-gpiod-out', config=self.output_lines) as request:
            while not self.event_no_longer_passive.is_set():
                # Sleep until next output toggle takes place or event is fired
                start_time = time.time()
                wakeup_ms = self.blinkrhythms.get_time_wakeup()
                event_occurred = self.event_wakeup_output.wait(timeout=wakeup_ms/1000)
                if event_occurred:
                    elapsed_time = time.time() - start_time
                    wakeup_ms = min(wakeup_ms, int(elapsed_time * 1000))
                    logger.debug(f'Woke up early after [{wakeup_ms}] due to notification')
                self.blinkrhythms.elapse_time(wakeup_ms, self.outputs)
                # Apply changes output values
                outputs_new = self.outputs.get_changes_and_apply()
                if len(outputs_new):
                    request.set_values(outputs_new)
                # Clear event to be able to set it again
                self.event_wakeup_output.clear()
            # Finally switch off everything
            outputs_new = { line: gpiod.line.Value.INACTIVE for line, output in self.outputs.items() }
            request.set_values(outputs_new)

    def thread_run(self):
        """Thread for monitoring input lines"""
        with self.chip.request_lines(consumer='looselycoupled-gpiod-in', config=self.input_lines) as request:
            while not self.event_no_longer_active.is_set():
                time.sleep(0.01)  # collect events for 10ms before listening (to reduce processing overhead)
                if request.wait_edge_events(timeout=1):
                    events = request.read_edge_events()
                    for event in events:
                        rising_edge = (event.event_type == event.Type.RISING_EDGE)
                        line_name = self.line_names.get(event.line_offset)
                        logger.info(f"Input event on line [{line_name}:{event.line_offset}:{event.line_seqno}]: {'rising edge' if rising_edge else 'falling edge'}")
                        self.trigger_event_threadsafe('changed_gpio_input', line=event.line_offset, line_name=line_name, line_seq={event.line_seqno}, rising_edge=rising_edge)
