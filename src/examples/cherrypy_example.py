# -*- coding: utf-8 -*-


import asyncio
import cherrypy
import jinja2
import logging
import os
import time

from looselycoupled import module_threaded


logger = logging.getLogger(__name__)


class WebApp():

    def __init__(self, exec_task_threadsafe, enqueue_task_threadsafe, trigger_event_threadsafe):
        """Instance initialization"""
        self.exec_task_threadsafe = exec_task_threadsafe
        self.enqueue_task_threadsafe = enqueue_task_threadsafe
        self.trigger_event_threadsafe = trigger_event_threadsafe
        self.jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')))
        self.lines = dict()

    def add_line(self, text):
        """Add a line to the line dictionary"""
        pos = len(self.lines)
        self.lines[pos] = text
        return pos

    @cherrypy.expose
    def index(self, action=None, id=None):
        """Show a list of existing machines"""
        #cherrypy.log('Index page requested', context='WEBAPP', severity=logging.INFO, traceback=False)
        logger.info(f'Index page requested, action [{action}], id [{id}]')
        
        if action == 'trigger':
            # Examples for calling modules' methods outside the event loop thread
            pos = self.exec_task_threadsafe('cherrypy_example.add_log_entry', metadata=None, text='This line was synchronously added by the module "cherrypy_example" from a non-coroutine in another thread')
            self.enqueue_task_threadsafe('cherrypy_example.add_log_entry', metadata=None, text='This line was asynchronously added by the module "cherrypy_example" from a non-coroutine in another thread')
            self.trigger_event_threadsafe('webpage_trigger')
            # Note: can't broadcast an event to our local event handler due to split horizon (don't send notifications to event source)            

        # Render page
        tmpl = self.jinja_env.get_template('index.html')
        return tmpl.render(sessiondata=cherrypy.session, outputlines=self.lines)

    def check_username_and_password(self, username, password):
        """Check whether provided username and password are valid when authenticating"""
        if (username != 'test') or (password != 'test'):
            return 'invalid username/password'
        cherrypy.log(f'User ["{username}"] logged in', context='WEBAPP', severity=logging.INFO, traceback=False)
        return

    def login_screen(self, from_page='..', username='', error_msg='', **kwargs):
        """Shows a login form"""
        tmpl = self.jinja_env.get_template('login.html')
        return tmpl.render(from_page=from_page, username=username, error_msg=error_msg).encode('utf-8')

    @cherrypy.expose
    def logout(self):
        """Ends the currently logged-in user's session"""
        username = cherrypy.session['username']
        cherrypy.session.clear()
        cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cherrypy.response.headers['Expires'] = '0'
        raise cherrypy.HTTPRedirect('/', 302)
        return f'"{username}" has been logged out'


def prepare_webapp(exec_task_threadsafe, enqueue_task_threadsafe, trigger_event_threadsafe):
    """Runs the CherryPy web application with the provided configuration data"""
    script_path = os.path.dirname(os.path.abspath(__file__))
    app = WebApp(exec_task_threadsafe, enqueue_task_threadsafe, trigger_event_threadsafe)
    # Use SSL if certificate files exist
    #= os.path.exists(cfg.sslcertfile) and os.path.exists(cfg.sslkeyfile)
    #sl:
    ## Use ssl/tls if certificate files are present
    #cherrypy.server.ssl_module = 'builtin'
    #cherrypy.server.ssl_certificate = cfg.sslcertfile
    #cherrypy.server.ssl_private_key = cfg.sslkeyfile
    #:
    #cherrypy.log(f'Not using SSL/TLS due to certificate files [{cfg.sslcertfile}] and [{cfg.sslkeyfile}] not being present', context='SETUP', severity=logging.WARNING, traceback=False)
    # Define socket parameters
    #cherrypy.config.update({'server.socket_host': cfg.socket_host,
    #                        'server.socket_port': cfg.socket_port,
    #                       })
    cherrypy.config.update({'server.socket_host': '0.0.0.0',
                            'server.socket_port': 8080,
                           })
    # Disable autoreload (cannot listen at a port <1024 after dropping root privileges)
    cherrypy.config.update({'engine.autoreload.on': False})
    cherrypy.config.update({'server.shutdown_timeout': 1})
    # Select environment
    #cherrypy.config.update({'environment': 'production'})
    # Configure the web application
    app_conf = {
       '/': {
            'tools.sessions.on': True,
    #        'tools.sessions.secure': ssl,
            'tools.sessions.httponly': True,
            'tools.staticdir.root': os.path.join(script_path, 'webroot'),
            'tools.session_auth.on': True,
            'tools.session_auth.login_screen': app.login_screen,
            'tools.session_auth.check_username_and_password': app.check_username_and_password,
            },
        '/static': {
            'tools.session_auth.on': False,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static'
        },
        '/favicon.ico':
        {
            'tools.session_auth.on': False,
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(script_path, 'webroot', 'static', 'favicon.ico')
        }
    }
    # Prepare CherryPy
    cherrypy.tree.mount(app, config=app_conf)
    # Return reference to app object
    return app


class CherryPyExample(module_threaded.ModuleThreaded):
    """Application module for a CherryPy webserver"""

    async def initialize(self):
        """Module initialization"""
        self.app = prepare_webapp(self.exec_task_threadsafe, self.enqueue_task_threadsafe, self.trigger_event_threadsafe)

    async def add_log_entry(self, metadata, text):
        """Adds a log entry to the log dictionary"""
        return self.app.add_line(text)

    async def on_my_simple_example_event(self, metadata, param):
        """React on event notification"""
        await self.add_log_entry(metadata, param)

    def thread_run(self):
        logger.info('Starting CherryPy webserver...')
        cherrypy.engine.start()
        while not self.event_no_longer_active.is_set():
            time.sleep(1)
        logger.info('Stopping CherryPy webserver...')
        cherrypy.engine.exit()
        # Don't call the following as it also attempts to wait for non-CherryPy-threads in a blocking manner
        #cherrypy.engine.block()  # wait for the engine to complete the shutdown
        logger.info('CherryPy webserver stopped')


module_class = CherryPyExample


if __name__ == '__main__':
    prepare_webapp()
    cherrypy.engine.start()
    cherrypy.engine.block()
