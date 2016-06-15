# tests.test_simulation.test_network
# Tests for the simulation network.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 16:50:07 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_network.py [945ecd7] benjamin@bengfort.com $

"""
Tests for the simulation network.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.exceptions import UnknownType
from cloudscope.simulation.network import Connection
from cloudscope.simulation.network import CONSTANT, VARIABLE, NORMAL


##########################################################################
## Connection Tests
##########################################################################

class ConnectionTests(unittest.TestCase):

    def test_constant_latency(self):
        """
        Test constant latency connections.
        """
        conn = Connection(None, None, None, latency=300, connection=CONSTANT)
        for idx in xrange(5000):
            self.assertEqual(conn.latency(), 300)

        # Test latency invariant: latency is an integer
        with self.assertRaises(AssertionError):
            conn = Connection(None, None, None, latency=(300, 1200), connection=CONSTANT)
            conn.latency()

    def test_variable_latency(self):
        """
        Test variable latency connections.
        """
        conn = Connection(None, None, None, latency=(300, 1200), connection=VARIABLE)
        for idx in xrange(5000):
            self.assertGreaterEqual(conn.latency(), 300)
            self.assertLessEqual(conn.latency(), 1200)

        # Test latency invariant: latency is an tuple
        with self.assertRaises(AssertionError):
            conn = Connection(None, None, None, latency=300, connection=VARIABLE)
            conn.latency()

    def test_normal_latency(self):
        """
        Test normal latency connections.
        """
        conn  = Connection(None, None, None, latency=(30, 5), connection=NORMAL)
        total = 0

        # Create sample latencies
        for idx in xrange(5000):
            latency = conn.latency()
            total  += latency

            # Ensure that the latency is bounded to the normal distribution
            self.assertGreater(latency, 0, "latency cannot be less than zero!")
            self.assertLess(latency, 60, "latency is greater than 6 std devs from the mean?!")

        # Test the mean
        mean = float(total) / 5000.0
        self.assertLess(30.0-mean, 1, "latency mean is not close enough to normal")

        # Test latency invariant: latency is a tuple
        with self.assertRaises(AssertionError):
            conn = Connection(None, None, None, latency=300, connection=NORMAL)
            conn.latency()

    def test_weird_connection_type(self):
        """
        Ensure that connections can only be constant, normal, or variable
        """
        conn = Connection(None, None, None, latency=(5, 100), connection="weird")
        with self.assertRaises(UnknownType):
            conn.latency()

    def test_bad_latency_type(self):
        """
        Ensure that the latency is a tuple or a list
        """
        conn = Connection(None, None, None, connection="weird")
        with self.assertRaises(AssertionError):
            conn.latency()
