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
Testing the analysis utilities package
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
        self.assertEqual(result[key], 230400)

    def test_handle_recv(self):
        """
        Test the recv result handler
        """
        key = 'recv'
        result = self.handler(
            key, self.results.results[key]
        )

        self.assertIn(key, result)
        self.assertEqual(result[key], 230398)

        key = 'mean message latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 50.0125, places=4)

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
        self.assertEqual(result[key], 6)

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
        self.assertEqual(result[key], 12)

    def test_handle_empty_reads(self):
        """
        Test the empty reads result handler
        """
        key = 'empty reads'
        result = self.handler(
            key, self.results.results[key]
        )

        self.assertIn(key, result)
        self.assertEqual(result[key], 4)

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
        self.assertEqual(result[key], 2)

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
        self.assertEqual(result[key], 9)

        key = 'mean visibility latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 148.2727, places=4)

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
        self.assertEqual(result[key], 9)

        key = 'mean commit latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 203.4545, places=4)

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
        self.assertEqual(result[key], 11)

        key = 'mean write latency (ms)'
        self.assertIn(key, result)
        self.assertAlmostEqual(result[key], 36.3636, places=4)
