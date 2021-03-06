# tests.test_simulation
# Tests for the simulation package.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 16:49:20 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [945ecd7] benjamin@bengfort.com $

"""
Tests for the simulation package.
"""

##########################################################################
## Imports
##########################################################################

import simpy

try:
    from unittest import mock
except ImportError:
    import mock

from cloudscope.replica import Replica, Location, Consistency, Device
from cloudscope.dynamo import Sequence
from cloudscope.simulation.base import Simulation
from cloudscope.results import Results


MockEnvironment = mock.create_autospec(simpy.Environment, autospec=True)
MockSimulation  = mock.create_autospec(Simulation, autospec=True)
MockResults     = mock.create_autospec(Results, autospec=True)
MockReplica     = mock.create_autospec(Replica, autospec=True)
sequence        = Sequence()

def get_mock_simulation(**kwargs):
    simulation     = MockSimulation()
    simulation.env = MockEnvironment()
    simulation.results = MockResults()

    simulation.__name__ = "MockSimulation"
    # Set specific properties and attributes
    simulation.env.process = mock.MagicMock()
    simulation.env.now  = kwargs.get('now', 42)
    simulation.replicas = [
        get_mock_replica(simulation) for x in xrange(kwargs.get('replicas', 5))
    ]

    return simulation


def get_mock_replica(simulation, **kwargs):
    kwargs['id']    = kwargs.get('id', "r{}".format(sequence.next()))
    kwargs['type']  = kwargs.get('type', Device.DESKTOP)
    kwargs['label'] = kwargs.get('label', "desktop-{}".format(kwargs['id']))
    kwargs['location']    = kwargs.get('location', Location.WORK)
    kwargs['consistency'] = kwargs.get('consistency', Consistency.STRONG)
    kwargs['env']   = simulation.env

    replica = Replica(simulation)
    replica = mock.create_autospec(replica, instance=True)
    replica.__name__ = "MockReplica"
    replica.sim = simulation

    for key, val in kwargs.items():
        setattr(replica, key, val)

    return replica
