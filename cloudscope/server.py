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

import os
import sys
import urllib
import urlparse
import posixpath
import cloudscope

from cloudscope.config import settings
from cloudscope.utils.logger import ServerLogger
from cloudscope.exceptions import ServerError, ImproperlyConfigured

from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler


##########################################################################
## Module Constants
##########################################################################

ADDR   = "localhost"
PORT   = 8080


##########################################################################
## CloudScope Request Handler
##########################################################################

class CloudScopeHandler(SimpleHTTPRequestHandler):
    """
    Returns files from the site directory rather than the working directory.
    """

    server_version = "CloudScopeHTTP/{}".format(cloudscope.get_version())

    def log_request(self, code='-', size='-'):
        """
        Eventually we will have to brick this method, but for now we're going
        to pass it through to the server logger.
        """
        message = '"{}" {} {}'.format(self.requestline, code, size)
        self.server.logger.info(message)

    def log_error(self, format, *args):
        """
        Pass through to the error logger rather than sys.stderr.
        """
        message = format % args
        self.server.logger.error(message)

    def translate_path(self, path):
        """
        Finds the absolute path of the requested file by referring to the
        htdocs variable in the server (e.g. the root of the files.)
        """
        # Alias some helpers from the server
        logger = self.server.logger
        htdocs = self.server.htdocs

        # Parse the result into a normalized path
        result = urlparse.urlparse(urllib.unquote(path).decode('utf-8'))
        path   = posixpath.normpath(result.path)

        # Break apart path and htdocs as the root
        parts  = filter(None, path.split("/"))
        parts.insert(0, htdocs)
        return os.path.join(*parts)

    def redirect(self, path, temporary=True):
        """
        Sends a redirect header with the new location.
        """
        self.send_response(302 if temporary else 301)
        self.send_header('Location', path)
        self.end_headers()

##########################################################################
## CloudScope Web Server
##########################################################################

class CloudScopeWebServer(HTTPServer):
    """
    Simple webserver that serves static files for cloudscope.
    """

    def __init__(self, **kwargs):
        self.logger = ServerLogger()
        self.htdocs = kwargs.get('htdocs', settings.site.htdocs)

        if not os.path.exists(self.htdocs):
            raise ImproperlyConfigured(
                "Root web directory, {!r} does not exist!".format(self.htdocs)
            )

        if not os.path.isdir(self.htdocs):
            raise ImproperlyConfigured(
                "Web docs root, {!r} is not a directory!".format(self.htdocs)
            )

        HTTPServer.__init__(self, (ADDR, PORT), CloudScopeHandler)

    def run(self):
        """
        Runs the webserver.
        """
        # Log startup
        self.logger.info(
            "Starting webserver at http://{}:{}".format(ADDR, PORT)
        )

        try:
            self.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            # Flush that pesky ^C
            sys.stdout.write("\r")
            sys.stdout.flush()

            # Log and shutdown.
            self.logger.info("Received shutdown request. Shutting down...")
            self.shutdown()
            self.logger.info("Server successfully stopped")
