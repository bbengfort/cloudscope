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

    def assertReliableResults(self, results):
        """
        Performs generic checking for the results object.
        """

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

        metrics = [
            u'tag size', u'session length', u'read', u'read latency',
            u'write', u'visibility latency',
        ]

        for metric in metrics:
            self.assertIn(metric, results['results'])
            self.assertGreater(len(results['results'][metric]), 0)

    @unittest.skip("See issue #45")
    def test_eventual_simulation(self):
        """
        Run the eventually consistent simulation without errors
        """
        # Load the simulation
        with open(EVENTUAL, 'r') as fobj:
            sim = ConsistencySimulation.load(fobj, max_sim_time=100000)

        # Run the simulation
        sim.run()

        # Dump the results for testing
        output = StringIO()
        sim.results.dump(output)

        # Get the results from the simulation
        output.seek(0)
        results = json.load(output)

        # Check the results
        self.assertReliableResults(results)

    @unittest.skip("See issue #49")
    def test_raft_simulation(self):
        """
        Run the raft consensus simulation without errors
        """
        # Load the simulation
        with open(RAFT, 'r') as fobj:
            sim = ConsistencySimulation.load(fobj, max_sim_time=100000)

        # Run the simulation
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
        # Load the simulation
        with open(TAG, 'r') as fobj:
            sim = ConsistencySimulation.load(
                fobj, max_sim_time=100000, objects=10
            )

        # Run the simulation
        sim.run()

        # Dump the results for testing
        output = StringIO()
        sim.results.dump(output)

        # Get the results from the simulation
        output.seek(0)
        results = json.load(output)

        # Check the results
        self.assertReliableResults(results)
