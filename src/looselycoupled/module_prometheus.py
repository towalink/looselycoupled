# -*- coding: utf-8 -*-

"""module_prometheus.py: This module exposes metrics to Prometheus via an http(s) server on port 9090 (by default)."""

# Note: Configuration is done in the application's config file in section "prometheus".
#
# Documentation links:
#   https://prometheus.github.io/client_python/
#   https://prometheus.io/docs/practices/naming/
# Alternative to serving via http(s) (not used/implemented here): https://prometheus.github.io/client_python/exporting/textfile/

import asyncio
import base64
import logging
import http.server
import os
import ssl
import threading

try:
    import prometheus_client
except ModuleNotFoundError:
    from . import mock_prometheus as prometheus_client

from looselycoupled import configuration
from looselycoupled import module_threaded


logger = logging.getLogger(__name__)
cfg = configuration.get_config()


class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Request handler for service metrics requests"""

    def __init__(self, lock, *args, **kwargs):
        """Instance initialization"""
        self.lock = lock
        self.username = cfg.get_item('prometheus.username')  # credentials for basic auth
        self.password = cfg.get_item('prometheus.password')
        if (self.username is not None) and (self.password is not None):
            logger.info('Using basic authentication for serving metric data')
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        # Handle authentication
        if (self.username is not None) and (self.password is not None):
            # Perform basic authentication
            auth_header = self.headers.get('Authorization')
            if auth_header is None:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Metrics"')
                self.end_headers()
                return

            # Verify credentials
            auth_type, credentials = auth_header.split(' ')
            username, password = base64.b64decode(credentials).decode().split(':')
            if (auth_type != 'Basic') or (username != self.username) or (password != self.password):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'Invalid authentication type or invalid credentials.')
                return
        # Serve metrics
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', prometheus_client.CONTENT_TYPE_LATEST)
            self.end_headers()
            with self.lock:
                self.wfile.write(prometheus_client.generate_latest())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found. Use "/metrics".')


class ModulePrometheus(module_threaded.ModuleThreaded):
    """Application module for exporting metrics for collection by Prometheus"""

    async def initialize(self):
        """Module initialization"""
        self.lock = threading.Lock()
        self.metrics = dict()

    async def set_gauge_value(self, metadata, metric, **kwargs):
        """Set metric value of type Gauge after ensuring metric exists"""
        # Check arguments for labels etc.
        documentation = '[no documentation provided]'
        labels = dict()
        value = None
        for key, data in kwargs.items():
            if key.startswith('label_'):
                labels[key[6:]] = data
            elif key == 'documentation':
                documentation = data
            elif key == 'value':
                value = data
            else:
                raise ValueError(f'Unexpected argument [{key}={value}]')
        # Create metric if not yet present and finally set value
        with self.lock:
            if metric not in self.metrics:
                self.metrics[metric] = prometheus_client.Gauge(metric, documentation, labels.keys())
            if value:
                if len(labels):
                    self.metrics[metric].labels(**labels).set(value)
                else:
                    self.metrics[metric].set(value)

    def thread_run_passively(self):
        """Thread for serving http requests"""
        # Initialization
        port = cfg.get_item('prometheus.port', 9090)
        httpd = http.server.HTTPServer(('0.0.0.0', port), lambda *args, **kwargs: HTTPRequestHandler(self.lock, *args, **kwargs))
        # Handle SSL/TLS if key files are present
        keyfile = cfg.get_item('prometheus.keyfile', os.path.join(cfg.filedir, 'prometheus_key.pem'))
        certfile = cfg.get_item('prometheus.certfile', os.path.join(cfg.filedir, 'prometheus_cert.pem'))
        if os.path.isfile(keyfile) and os.path.isfile(certfile):
            #old way: httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=keyfile, certfile=certfile, server_side=True)
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(keyfile=keyfile, certfile=certfile)
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
        else:
            logger.warn(f'Not using SSL/TLS as both the keyfile [{keyfile}] and the certfile [{certfile}] need to be present')
        logger.info(f'Starting metrics server on port {port}')
        # Server requests until application needs to quit
        httpd.timeout = 1  # set a timeout for periodic stop checks
        try:
            while not self.event_no_longer_passive.is_set():
                httpd.handle_request()
        finally:
            httpd.server_close()


module_class = ModulePrometheus
