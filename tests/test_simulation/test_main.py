# tests.test_simulation.test_main
# Test the primary consistency simulation mechanism
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Mar 11 08:08:29 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_main.py [] benjamin@bengfort.com $

"""
Test the primary consistency simulation mechanism.
These tests act as integration tests: running the entire simulation.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import logging
import unittest

from cStringIO import StringIO

try:
    from unittest import mock
except ImportError:
    import mock

from cloudscope.version import get_version
from cloudscope.simulation.main import ConsistencySimulation

##########################################################################
## Fixtures
##########################################################################

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")
RAFT     = os.path.join(FIXTURES, "raft.json")
EVENTUAL = os.path.join(FIXTURES, "eventual.json")
TAG      = os.path.join(FIXTURES, "tag.json")


def load_simulation(path, **kwargs):
    """
    Helper function for loading a simulation consistently.
    """
    defaults = {
        'max_sim_time': 100000,
        'objects': 10,
    }
    defaults.update(kwargs)

    with open(path, 'r') as fobj:
        return ConsistencySimulation.load(fobj, **defaults)


##########################################################################
## Simulation Tests
##########################################################################

class SimulationTests(unittest.TestCase):

    def setUp(self):
        # Disable logging
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Re-enable logging
        logging.disable(logging.NOTSET)

    def assertReliableResults(self, results, metrics=None):
        """
        Performs generic checking for the results object.
        """
        metrics = metrics or set([])

        topkeys = [
            u'settings', u'results', u'randseed', u'simulation', u'version',
            u'timer', u'timesteps', u'topology'
        ]

        for key in topkeys:
            self.assertIn(key, results)

        self.assertEqual(results['version'], get_version())
        # self.assertEqual(results['timesteps'], 100000) # TODO: fix this to make it work!
        self.assertEqual(len(results['topology'].get('nodes', [])), 3)
        self.assertEqual(len(results['topology'].get('links', [])), 3)
        self.assertIn('meta', results['topology'])

        # Required Metrics
        required = {
            u'read', u'read latency',
            u'write', u'write latency', u'visibility latency',
        } | metrics

        # Optional Metrics
        optional = {
            u'sent', u'recv', u'commit latency', u'stale reads'
        }

        for metric in required:
            self.assertIn(metric, results['results'], "Missing '{}' metric from results".format(metric))
            self.assertGreater(len(results['results'][metric]), 0)

        for metric in results['results'].keys():
            self.assertIn(metric, required | optional, "Unknown metric named '{}'".format(metric))


    # @unittest.skip("See issue #45")
    def test_eventual_simulation(self):
        """
        Run the eventually consistent simulation without errors
        """
        # Load & Run the simulation
        sim = load_simulation(EVENTUAL)
        sim.run()

        # Dump the results for testing
        output = StringIO()
        sim.results.dump(output)

        # Get the results from the simulation
        output.seek(0)
        results = json.load(output)

        # Check the results
        self.assertReliableResults(results)

    def test_raft_simulation(self):
        """
        Run the raft consensus simulation without errors
        """
        # Load & Run the simulation
        sim = load_simulation(RAFT)
        sim.run()

        # Dump the results for testing
        output = StringIO()
        sim.results.dump(output)

        # Get the results from the simulation
        output.seek(0)
        results = json.load(output)

        # Check the results
        self.assertReliableResults(results)

    def test_tag_simulation(self):
        """
        Run the tag consensus simulation without errors
        """
        # Load & Run the simulation
        sim = load_simulation(TAG)
        sim.run()

        # Dump the results for testing
        output = StringIO()
        sim.results.dump(output)

        # Get the results from the simulation
        output.seek(0)
        results = json.load(output)

        # Check the results
        tag_metrics = {u'tag size', u'session length'}
        self.assertReliableResults(results, metrics=tag_metrics)
