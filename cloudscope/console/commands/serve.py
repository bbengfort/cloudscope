# cloudscope.console.commands.serve
# Runs the cloudscope development/debugging web server.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 14:25:15 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: serve.py [123e7af] benjamin@bengfort.com $

"""
Runs the cloudscope development/debugging web server.
"""

##########################################################################
## Imports
##########################################################################

from commis import Command
from cloudscope.config import settings
from cloudscope.server import CloudScopeWebServer


##########################################################################
## Command
##########################################################################

class ServeCommand(Command):

    name = 'serve'
    help = 'a simple development/debugging web server.'
    args = {
        ('-P', '--port'): {
            'type': int,
            'default': settings.server.port,
            'help': 'the port number to run the server on.'
        },
        ('-A', '--addr'): {
            'type': str,
            'default': settings.server.address,
            'help': 'the IP address to run the server on.'
        },
        '--htdocs': {
            'type': str,
            'default': settings.site.htdocs,
            'help': 'the root directory for the web files.'
        }
    }

    def handle(self, args):
        httpd = CloudScopeWebServer(
            htdocs = args.htdocs,
            addr   = args.addr,
            port   = args.port
        )

        httpd.run()
        return ""
