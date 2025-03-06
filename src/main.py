#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""main.py: Example for using event framework."""

__author__ = "Dirk Henrici"
__license__ = "AGPL3"
__email__ = "towalink.looselycoupled@henrici.name"


import getopt
import logging
import sys

from looselycoupled import configuration
from looselycoupled import modulemanager
from looselycoupled import module_clickhandler
from looselycoupled import module_prometheus
from examples import cherrypy_example
from examples import controller_example
from examples import gpiod_example
from examples import simple_example


class App():

    def display_usage(self):
        """Displays usage information"""
        print('Usage: %s [-?|--help] [-l|--loglevel debug|info|error] [-v|--verbose' % sys.argv[0])
        print('Starts the service')
        print()
        print('  -?, --help                        show program usage')
        print('  -l, --loglevel debug|info|error   set the level of debug information')
        print('                                    default: info')
        print('  -v, --verbose                     log to console')
        print()

        print('Example: %s --loglevel debug --verbose' % sys.argv[0])
        print()

    def parse_opts(self):
        """Parse and return command line arguments"""
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'l:v:?', ['help', 'loglevel=', 'verbose'])
        except getopt.GetoptError as ex:
            print(ex)  # will print something like "option -a not recognized"
            self.display_usage()
            sys.exit(2)
        loglevel = logging.INFO
        verbose = False
        for o, a in opts:
            if o in ('-?', '--help'):
                self.display_usage()
                sys.exit()
            elif o in ('-l', '--loglevel'):
                a = a.lower().strip()
                if a == 'debug':
                    loglevel = logging.DEBUG
                elif a == 'info':
                    loglevel = logging.INFO
                elif a == 'error':
                    loglevel = logging.ERROR
                else:
                    print('invalid loglevel')
                    self.display_usage()
                    sys.exit(2)
            elif o in ('-v', '--verbose'):
                verbose = True
            else:
                assert False, 'unhandled option'
        if len(args) != 0:
            print('invalid argument')
            self.display_usage()
            sys.exit(2)
        return loglevel, verbose

    def configure_logging(self, loglevel, verbose):
        """Configure the logging module"""
        format = '%(asctime)s %(levelname)s %(module)s: %(message)s'
        #if verbose:
        #    logging.basicConfig(format=format, stream=sys.stdout, level=loglevel);
        #else:
        #    logging.basicConfig(format=format, level=loglevel); # use %(name)s instead of %(module) to include hierarchy information, see https://docs.python.org/2/library/logging.html
        # Due to trouble with basicConfig above (only works if called very early), now changed to the following
        root_handler = logging.getLogger()
        formatter = logging.Formatter(format)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_handler.addHandler(stream_handler)
        root_handler.setLevel(loglevel)
        #print([logging.getLogger(name).name for name in logging.root.manager.loggerDict]);
        #logging.getLogger('etcd').setLevel(logging.INFO); # reduce loglevel for etcd library

    def run(self, appmodules=None):
        """Run the application"""
        loglevel, verbose = self.parse_opts()
        self.configure_logging(loglevel, verbose)
        exception_path = './tmp_exceptions.log'
        modulemanager.ModuleManager(appmodules, exception_path=exception_path).run()


if __name__ == "__main__":
    configuration.get_config().load_config('/etc/mytool/config.yaml')
    app = App()
    appmodules = {'simple_example' : simple_example}
    appmodules.update({'controller_example' : controller_example})
    appmodules.update({'gpiod_example' : gpiod_example})
    appmodules.update({'cherrypy_example' : cherrypy_example})
    appmodules.update({'clickhandler' : module_clickhandler})
    appmodules.update({'prometheus' : module_prometheus})
    app.run(appmodules=appmodules)
