# tests.test_simulation
# Tests for the simulation package.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 16:49:20 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [] benjamin@bengfort.com $

"""
Tests for the simulation package.
"""

##########################################################################
## Imports
##########################################################################

try:
    from unittest import mock
except ImportError:
    import mock


def get_mock_simulation(**kwargs):
    simulation = mock.MagicMock()
    simulation.env.now = kwargs.get('now', 42)

    return simulation

def get_mock_replica(**kwargs):
    from cloudscope.simulation.replica import Replica
    return Replica(get_mock_simulation())
