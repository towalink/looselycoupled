import logging
import time


logger = logging.getLogger(__name__)
logger.warn('Using gpiod mock!')


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
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def wait_edge_events(self, *args, **kwargs):
        if (timeout := kwargs.get('timeout')) is not None:
            time.sleep(timeout)

    def set_values(self, outputs_new):
        logger.info(f'Setting outputs to [{outputs_new}]')

class LineSettings():
    def __init__(self, direction=None, edge_detection=None, bias=None, debounce_period=None, output_value=None):
        pass

