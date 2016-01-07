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

    url        = "http://localhost:8080"



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

##########################################################################
## Generate Site Settings
##########################################################################

settings = CloudScopeConfiguration.load()

if __name__ == '__main__':
    print settings
