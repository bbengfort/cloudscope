# tests.test_experiment
# Tests for the experiment generation utility.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Feb 23 08:09:12 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_experiment.py [] benjamin@bengfort.com $

"""
Tests for the experiment generation utility.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import unittest

from cloudscope.experiment import *
from cloudscope.exceptions import CannotGenerateExperiments

try:
    from unittest import mock
except ImportError:
    import mock

##########################################################################
## Fixtures
##########################################################################

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
TEMPLATE = os.path.join(FIXTURES, "simulation.json")

##########################################################################
## Helper Function Tests
##########################################################################

class ExperimentHelpersTests(unittest.TestCase):
    """
    Ensure the experiment helper functions behave as expected.
    """

    def test_spread_evenly(self):
        """
        Test the even spread across a domain
        """
        expected = [
            [0, 10],  [10, 20], [20, 30], [30, 40], [40, 50],
            [50, 60], [60, 70], [70, 80], [80, 90], [90, 100],
        ]

        self.assertEqual(expected, list(spread(10, 0, 100)))

    def test_spread_width(self):
        """
        Test the spread with a specified width
        """
        expected = [
            [0, 5],  [10, 15], [20, 25], [30, 35], [40, 45],
            [50, 55], [60, 65], [70, 75], [80, 85], [90, 95],
        ]

        self.assertEqual(expected, list(spread(10, 0, 100, 5)))

    def test_simple_nested_update(self):
        """
        Ensure that the nested update behaves like update
        """
        d = {'a': 1, 'b': 2, 'c': 3}
        u = {'c': 4, 'd': 5, 'e': 6}
        e = d.copy()
        e.update(u)
        self.assertEqual(e, nested_update(d,u))

    def test_nested_update(self):
        """
        Test the nested update function
        """
        d = {'I': {'A': {'a': 1}, 'B': {'a': 2}}}
        u = {'I': {'B': {'b': 4}}, 'II': {'A': {'a': 5}}}
        e = {'I': {'A': {'a': 1}, 'B': {'a': 2, 'b': 4}}, 'II': {'A': {'a': 5}}}

        self.assertEqual(nested_update(d,u), e)

##########################################################################
## Experiment Generator Tests
##########################################################################

class ExperimentGeneratorTests(unittest.TestCase):
    """
    Test the ExperimentGenerator base class.
    """

    def setUp(self):
        with open(TEMPLATE, 'r') as f:
            self.template = json.load(f)

    def tearDown(self):
        self.template = None

    def test_get_defaults(self):
        """
        Test that the options are set correctly on the experiment
        """
        users_opts = {'minimum': 1, 'maximum': 5, 'step': 2}
        generator  = ExperimentGenerator(self.template, users=users_opts)
        self.assertEqual(generator.options['users'], users_opts)

    def test_get_defaults_partial(self):
        """
        Test that partial options are set correctly on the experiment
        """
        users_opts = {'maximum': 5}
        generator  = ExperimentGenerator(self.template, users=users_opts)
        expected   = {'minimum': 1, 'maximum': 5, 'step': 1}
        self.assertEqual(generator.options['users'], expected)

    def test_users_defaults(self):
        """
        Assert that the experiment generator does one user by default
        """
        generator = ExperimentGenerator(self.template)
        expected = [1]
        self.assertEqual(list(generator.users()), expected)

    def test_user_generation(self):
        """
        Test the n_users on experiment generation
        """
        users_opts = {'minimum': 1, 'maximum': 5, 'step': 2}
        expected   = [1, 3, 5]
        generator  = ExperimentGenerator(self.template, users=users_opts)
        self.assertEqual(list(generator.users()), expected)

    def test_interface(self):
        """
        Test the experiment generator interface
        """
        with self.assertRaises(NotImplementedError):
            generator  = ExperimentGenerator(self.template)
            for experiment in generator.generate():
                print experiment

    def test_iterator(self):
        """
        Test the experiment generator iterator interface
        """
        expected   = [1,2,3]
        generator  = ExperimentGenerator(self.template)
        generator.generate = mock.MagicMock(return_value=expected)

        self.assertEqual(len(generator), 3, "len not computed correctly")
        self.assertEqual(list(generator), expected)



##########################################################################
## Latency Variation Tests
##########################################################################

class LatencyVariationTests(unittest.TestCase):
    """
    Test the LatencyVariation experiment generator.
    """

    def setUp(self):
        with open(TEMPLATE, 'r') as f:
            self.template = json.load(f)

    def tearDown(self):
        self.template = None

    def test_get_defaults(self):
        """
        Test that the options are set correctly on the experiment
        """
        users_opts   = {'minimum': 1, 'maximum': 5, 'step': 2}
        latency_opts = {'minimum': 15, 'maximum': 6000, 'max_range': 800}
        generator    = LatencyVariation(self.template, users=users_opts, latency=latency_opts)

        self.assertEqual(generator.options['users'], users_opts)
        self.assertEqual(generator.options['latency'], latency_opts)

    def test_get_defaults_partial(self):
        """
        Test that partial options are set correctly on the experiment
        """
        users_opts   = {'maximum': 5}
        latency_opts = {'max_range': 800}
        generator    = LatencyVariation(self.template, users=users_opts, latency=latency_opts)
        expected     = {
            'users': {'minimum': 1, 'maximum': 5, 'step': 1},
            'latency': {'minimum': 5, 'maximum': 3000, 'max_range': 800}
        }

        self.assertEqual(generator.options, expected)

    def test_latency_generator(self):
        """
        Test the latencies generator function
        """
        latency   = {'minimum': 0, 'maximum': 1000, 'max_range': 1000}
        generator = LatencyVariation(self.template, latency=latency, count=10)
        expected  = [
            ([0, 100], 50),
            ([100, 200], 150),
            ([200, 300], 250),
            ([300, 400], 350),
            ([400, 500], 450),
            ([500, 600], 550),
            ([600, 700], 650),
            ([700, 800], 750),
            ([800, 900], 850),
            ([900, 1000], 950),
        ]

        self.assertEqual(list(generator.latencies(10)), expected)

    def test_generate(self):
        """
        Test the experimental generation with a single user.
        """
        latency   = {'minimum': 0, 'maximum': 1000, 'max_range': 1000}
        generator = LatencyVariation(self.template, latency=latency, count=10)
        expected  = [
            # (variable, constant, election, heartbeat, nusers)
            ([0, 100], 50, [500, 1000], 250, 1),
            ([100, 200], 150, [1500, 3000], 750, 1),
            ([200, 300], 250, [2500, 5000], 1250, 1),
            ([300, 400], 350, [3500, 7000], 1750, 1),
            ([400, 500], 450, [4500, 9000], 2250, 1),
            ([500, 600], 550, [5500, 11000], 2750, 1),
            ([600, 700], 650, [6500, 13000], 3250, 1),
            ([700, 800], 750, [7500, 15000], 3750, 1),
            ([800, 900], 850, [8500, 17000], 4250, 1),
            ([900, 1000], 950, [9500, 19000], 4750, 1),
        ]

        for expected, experiment in zip(expected, generator):
            vrbl, cons, eto, hb, nusers = expected
            self.assertEqual(experiment['meta']['users'], nusers)

            for node in experiment['nodes']:
                if node['consistency'] == 'strong':
                    self.assertEqual(node['election_timeout'], eto)
                    self.assertEqual(node['heartbeat_interval'], hb)

            for link in experiment['links']:
                if link['connection'] == 'variable':
                    self.assertEqual(link['latency'], vrbl)
                else:
                    self.assertEqual(link['latency'], cons)

    def test_num_experiments(self):
        """
        Test the number of experiments with both user and latency dimensions
        """
        users     = {'maximum': 5, 'step': 2}
        latency   = {'minimum': 0, 'maximum': 1000, 'max_range': 1000}
        generator = LatencyVariation(self.template, users=users, latency=latency, count=10)
        self.assertEqual(30, len(generator))
