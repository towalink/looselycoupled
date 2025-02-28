import logging
import time


logger = logging.getLogger(__name__)
logger.warn('Using prometheus-client mock! Install "prometheus-client" package to change this.')


CONTENT_TYPE_LATEST = 'text/plain'

def generate_latest():
    return b'mock nodata'


class Gauge():
    def __init__(self, *args, **kwargs):
        pass
