# cloudscope.config
# Configuration for the CloudScope project.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Jan 07 16:13:49 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: config.py [] benjamin@bengfort.com $

"""
Configuration for the CloudScope project.
"""

##########################################################################
## Imports
##########################################################################

import os

from confire import Configuration

##########################################################################
## Base Paths
##########################################################################

PROJECT  = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class SiteConfiguration(Configuration):
    """
    Configuration variables to add to the site.
    """

    htdocs     = os.path.join(PROJECT, "deploy")
    url        = "http://localhost:8080"


##########################################################################
## Logging Configuration
##########################################################################

class LoggingConfiguration(Configuration):
    """
    Very specific logging configuration instructions (does not provide the
    complete configuration as available in the python logging module). See
    the `cloudscope.utils.logger` module for more info.
    """

    level   = "INFO"
    logfmt  = "[%(asctime)s] %(levelname)s %(message)s"
    datefmt = "%d/%b/%Y %H:%M:%S"
    disable_existing_loggers = False


##########################################################################
## Application Configuration
##########################################################################

class CloudScopeConfiguration(Configuration):

    CONF_PATHS = [
        '/etc/cloudscope.yaml',
        os.path.expanduser('~/.cloudscope.yaml'),
        os.path.abspath('conf/cloudscope.yaml')
    ]

    debug     = False
    testing   = True
    site      = SiteConfiguration()
    logging   = LoggingConfiguration()

##########################################################################
## Generate Site Settings
##########################################################################

settings = CloudScopeConfiguration.load()

if __name__ == '__main__':
    print settings
