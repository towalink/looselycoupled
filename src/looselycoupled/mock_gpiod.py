from collections import namedtuple
import logging
import sys
import time

logger = logging.getLogger(__name__)
logger.warn('Using gpiod mock!')

try:
    import keyboard
except ImportError:
    logger.warn('Python module [keyboard] not installed; checking on keyboad events will not be possible')


class Event(namedtuple('Event', ('event_type', 'line_offset', 'line_seqno'))):
    class Type:
        RISING_EDGE = 1
        FALLING_EDGE = 2


class line:
    class Direction:
        INPUT = None
        OUTPUT = None
    class Edge:
        BOTH = None
    class Bias:
        PULL_DOWN = None
        PULL_UP = None
    class Value:
        ACTIVE = 1
        INACTIVE = 0


class Chip():
    def __init__(self, *args, **kwargs):
        pass

    def request_lines(self, *args, **kwargs):
        # Return an instance of LineRequest which will manage the use of requested lines
        return LineRequest()


class LineRequest:
    def __init__(self, *args, **kwargs):
        self.key_pressed = False
        self.key_event = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def wait_edge_events(self, *args, **kwargs):
        if (timeout := kwargs.get('timeout')) is not None:
            if 'keyboard' in sys.modules:
                if self.key_pressed != keyboard.is_pressed('escape'):
                    self.key_pressed = keyboard.is_pressed('escape')
                    self.key_event = True
                    return True
            else:
                time.sleep(timeout)
        return False

    def read_edge_events(self):
        if self.key_event:
            self.key_event = False  # clear event
            event = Event(self.key_pressed, 22, 0)
            return [ event ]
        else:
            return []

    def set_values(self, outputs_new):
        logger.info(f'Setting outputs to [{outputs_new}]')


class LineSettings():
    def __init__(self, direction=None, edge_detection=None, bias=None, debounce_period=None, output_value=None):
        pass

