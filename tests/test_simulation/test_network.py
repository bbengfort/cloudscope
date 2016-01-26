# tests.test_simulation.test_network
# Tests for the simulation network.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 16:50:07 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_network.py [] benjamin@bengfort.com $

"""
Tests for the simulation network.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.exceptions import UnknownType
from cloudscope.simulation.network import Connection
from cloudscope.simulation.network import CONSTANT, VARIABLE


##########################################################################
## Connection Tests
##########################################################################

class ConnectionTests(unittest.TestCase):

    def test_constant_latency(self):
        """
        Test constant latency connections.
        """
        conn = Connection(None, None, None, latency=300, type=CONSTANT)
        for idx in xrange(5000):
            self.assertEqual(conn.latency(), 300)

        # Test latency invariant: latency is an integer
        with self.assertRaises(AssertionError):
            conn = Connection(None, None, None, latency=(300, 1200), type=CONSTANT)
            conn.latency()

    def test_variable_latency(self):
        """
        Test variable latency connections.
        """
        conn = Connection(None, None, None, latency=(300, 1200), type=VARIABLE)
        for idx in xrange(5000):
            self.assertGreaterEqual(conn.latency(), 300)
            self.assertLessEqual(conn.latency(), 1200)

        # Test latency invariant: latency is an tuple
        with self.assertRaises(AssertionError):
            conn = Connection(None, None, None, latency=300, type=VARIABLE)
            conn.latency()

    def test_weird_connection_type(self):
        """
        Ensure that connections can only be constant or variable
        """
        conn = Connection(None, None, None, type="weird")
        with self.assertRaises(UnknownType):
            conn.latency()
