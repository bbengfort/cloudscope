# cloudscope.server
# A simple HTTP server to serve static files for development.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sat Jan 09 09:42:48 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: server.py [] benjamin@bengfort.com $

"""
A simple HTTP server to serve static files for development.
"""

##########################################################################
## Imports
##########################################################################

import logging

from BaseHTTPServer import HTTPServer
from cloudscope.config import settings
from SimpleHTTPServer import SimpleHTTPRequestHandler


##########################################################################
## Module Constants
##########################################################################

ADDR   = "localhost"
PORT   = 8080

logger = logging.getLogger('cloudscope.server')

##########################################################################
## CloudScope Request Handler
##########################################################################

class CloudScopeHandler(SimpleHTTPRequestHandler):
    """
    Returns files from the site directory rather than the working directory.
    """
    pass


##########################################################################
## CloudScope Web Server
##########################################################################

class CloudScopeWebServer(HTTPServer):
    """
    Simple webserver that serves static files for cloudscope.
    """

    def __init__(self, **kwargs):
        self.htdocs = kwargs.get('htdocs', settings.site.htdocs)
        HTTPServer.__init__(self, (ADDR, PORT), CloudScopeHandler)

    def run(self):
        """
        Runs the webserver.
        """
        logger.info(
            "Starting webserver at [{}]:[{}]".format(ADDR, PORT)
        )

        try:
            self.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Received shutdown request. Shutting down...")
            self.shutdown()
            logger.info("Server successfully stopped")
