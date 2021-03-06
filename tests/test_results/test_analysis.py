# tests.test_results.test_analysis
# Testing the analysis utilities package
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Jun 23 21:56:56 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_analysis.py [] benjamin@bengfort.com $

"""
Testing the analysis utilities package.

The results used in this analysis were generated by running the raft.json
topology in the deply data directory for 100000 timesteps and writing the
output results to the test fixtures results.json file.

The command is as follows:

    $ ./scope.py simulate deploy/data/raft.json \
        -o tests/fixtures/results.json \
        -t 100000

Import parameters that need to be set:

- trace_messages: true
- users: 5
- conflict_prob: 0.5
- election_timeout: [150, 300]
- heartbeat_interval: 75

Make sure that you run the simulation enough time such that there are stale
reads and commit latency recorded.
"""

##########################################################################
## Imports
##########################################################################

import os
import unittest

from cloudscope.results import Results
from cloudscope.results.analysis import *


##########################################################################
## Fixtures
##########################################################################

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")
RESULTS  = os.path.join(FIXTURES, "results.json")

##########################################################################
## Test Time Series Aggregator
##########################################################################


class TimeSeriesAggregatorTests(unittest.TestCase):

    def setUp(self):
        self.handler = TimeSeriesAggregator()
        with open(RESULTS, 'r') as f:
            self.results = Results.load(f)

    def tearDown(self):
        self.results = None
        self.handler = None

    def test_auto_default(self):
        """
        Test that unknown keys automatically default
        """
        key = "weird food key"
        result = self.handler(key, range(10))
        self.assertIn(key, result)
        self.assertEqual(result[key], 10)

    def test_handle_sent(self):
        """
        Test the sent result handler
        """
        key = 'sent'
        result = self.handler(
            key, self.results.results[key]
        )

        self.assertIn(key, result)
        self.assertEqual(result[key], 10762)

    def test_handle_recv(self):
        """
        Test the recv result handler
        """
        key = 'recv'
        result = self.handler(
            key, self.results.results[key]
        )

        self.assertIn(key, result)
        self.assertEqual(result[key], 10758)

        key = 'mean message latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 30.0644, places=4)

    def test_handle_read(self):
        """
        Test the read result handler
        """
        key = 'read'
        result = self.handler(
            key, self.results.results[key]
        )

        key = 'reads' # Renamed
        self.assertIn(key, result)
        self.assertEqual(result[key], 94)

    def test_handle_write(self):
        """
        Test the write result handler
        """
        key = 'write'
        result = self.handler(
            key, self.results.results[key]
        )

        key = 'writes' # Renamed
        self.assertIn(key, result)
        self.assertEqual(result[key], 70)

    def test_handle_empty_reads(self):
        """
        Test the empty reads result handler
        """
        key = 'empty reads'
        result = self.handler(
            key, self.results.results[key]
        )

        self.assertIn(key, result)
        self.assertEqual(result[key], 16)

    def test_handle_read_latency(self):
        """
        Test the read latency result handler
        """
        key = 'read latency'
        result = self.handler(
            key, self.results.results[key]
        )

        key = 'completed reads'
        self.assertIn(key, result)
        self.assertEqual(result[key], 78)

        key = 'mean read latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 0.0, places=4)

    def test_handle_stale_reads(self):
        """
        Test the stale reads result handler
        """
        key = 'stale reads'
        result = self.handler(
            key, self.results.results[key]
        )

        self.assertIn(key, result)
        self.assertEqual(result[key], 1)

        metrics = (
            ("cumulative read time staleness (ms)", 3034.4121),
            ("mean read time staleness (ms)", 3034.4121),
            ("mean read version staleness", 1.0),
        )

        for key, value in metrics:
            self.assertIn(key, result)
            self.assertAlmostEqual(result[key], value, places=4)

    def test_handle_visibility_latency(self):
        """
        Test the visibility latency result handler
        """
        key = 'visibility latency'
        result = self.handler(
            key, self.results.results[key]
        )

        key = 'visible writes'
        self.assertIn(key, result)
        self.assertEqual(result[key], 69)

        key = 'mean visibility latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 96.3727, places=4)

    def test_handle_commit_latency(self):
        """
        Test the commit latency result handler
        """
        key = 'commit latency'
        result = self.handler(
            key, self.results.results[key]
        )

        key = 'committed writes'
        self.assertIn(key, result)
        self.assertEqual(result[key], 69)

        key = 'mean commit latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 120.9669, places=4)

    def test_handle_write_latency(self):
        """
        Test the write latency result handler
        """
        key = 'write latency'
        result = self.handler(
            key, self.results.results[key]
        )

        key = 'completed writes'
        self.assertIn(key, result)
        self.assertEqual(result[key], 69)

        key = 'mean write latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 45.6957, places=4)
