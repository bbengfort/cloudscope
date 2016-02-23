# tests.test_results
# Tetings for the results collection and serialization tool.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Feb 23 11:04:04 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_results.py [] benjamin@bengfort.com $

"""
Tetings for the results collection and serialization tool.
"""

##########################################################################
## Imports
##########################################################################

import json
import unittest
import datetime

from dateutil.tz import tzutc
from cStringIO import StringIO
from cloudscope.results import *
from cloudscope.version import get_version
from cloudscope.utils.decorators import Timer

try:
    from unittest import mock
except ImportError:
    import mock

##########################################################################
## Results Tests
##########################################################################

class ResultsTests(unittest.TestCase):

    def assertKVEqual(self, key, val, obj):
        """
        Asserts a key is in obj and that it equals val.
        """
        self.assertIn(key, obj)
        self.assertEqual(obj[key], val)

    def test_results_base(self):
        """
        Test the basic properties of a result object
        """

        result = Results(simulation="Test Simulation")
        output = StringIO()
        result.dump(output)

        output.seek(0)
        output = json.load(output)

        self.assertKVEqual('simulation', "Test Simulation", output)
        self.assertKVEqual('version', get_version(), output)
        self.assertIn('randseed', output)
        self.assertIn('timesteps', output)
        self.assertIn('results', output)
        self.assertIn('timer', output)
        self.assertIn('settings', output)

    def test_results_update(self):
        """
        Test the ability to add series to the results
        """
        result = Results(simulation="Test Simulation")
        for x in xrange(1, 10):
            result.update('values', x)

        self.assertIn('values', result.results)
        self.assertEqual(result.results, {'values': [1,2,3,4,5,6,7,8,9]})

    def test_properties(self):
        """
        Test the properties of the simulation
        """
        result = Results(simulation="Test Simulation")

        timer  = Timer()
        timer.started  = 1
        timer.finished = 12
        timer.elapsed  = 11

        result.timer   = timer

        self.assertEqual(result.title, 'Test Simulation on Thu Jan 01 00:00:12 1970 +0000')
        self.assertEqual(result.finished, datetime.datetime(1970, 1, 1, 0, 0, 12, tzinfo=tzutc()))
