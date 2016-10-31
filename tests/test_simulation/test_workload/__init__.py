# tests.test_simulation.test_workload
# Testing the workload generation package in CloudScope.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Aug 01 17:40:00 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [9d50557] benjamin@bengfort.com $

"""
Testing the workload generation package in CloudScope.
"""

##########################################################################
## Imports
##########################################################################

try:
    from unittest import mock
except ImportError:
    import mock


##########################################################################
## Access Tracking
##########################################################################

class AccessTracking(object):

    def __init__(self, env):
        self.env     = env
        self.mock    = mock.Mock()
        self.history = []

    def __call__(self, *args, **kwargs):
        self.history.append(self.env.now)
        self.mock(*args, **kwargs)
        return args[0]

    @property
    def call_count(self):
        return self.mock.call_count
