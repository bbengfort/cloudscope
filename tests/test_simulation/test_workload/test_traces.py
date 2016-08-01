# tests.test_simulation.test_workload.test_traces
# Tests for the traces reply script methodology.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Aug 01 17:44:26 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_traces.py [] benjamin@bengfort.com $

"""
Tests for the traces reply script methodology.
"""

##########################################################################
## Imports
##########################################################################

import os
import simpy
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from cloudscope.replica import Location, Device
from cloudscope.exceptions import WorkloadException
from cloudscope.simulation.workload import TracesWorkload
from cloudscope.simulation.workload.traces import TracesParser
from cloudscope.simulation.workload.traces import TraceAccess, READ, WRITE
from tests.test_simulation import get_mock_simulation, get_mock_replica
from tests.test_simulation.test_workload import AccessTracking

##########################################################################
## Fixtures
##########################################################################

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures")
TRACES   = os.path.join(FIXTURES, "traces.tsv")


##########################################################################
## Traces Parser Tests
##########################################################################

class TracesParserTests(unittest.TestCase):
    """
    Test the trace file parsing mechanism.
    """

    def test_line_parsing(self):
        """
        Test that workload lines are parsed correctly
        """

        parser  = TracesParser(TRACES)
        value = parser.parse("  53    r1  B   read  ")
        self.assertEqual(value, TraceAccess(53, "r1", "B", "read"))

        value = parser.parse("2424.32 r9  write")
        self.assertEqual(value, TraceAccess(2424, "r9", None, "write"))

    def test_line_parse_failure(self):
        """
        Test that invalid lines raise an exception
        """
        parser  = TracesParser(TRACES)

        with self.assertRaises(WorkloadException):
            value = parser.parse("abcdefg")

        with self.assertRaises(WorkloadException):
            value = parser.parse("23  r2   A     touch")

        with self.assertRaises(WorkloadException):
            value = parser.parse("")

    def test_traces_read(self):
        """
        Test that a traces fixture can be read and parsed
        """
        parser  = TracesParser(TRACES)
        count = 0

        for access in parser:
            count += 1
            self.assertIsInstance(access, TraceAccess)

        self.assertEqual(count, 18)

##########################################################################
## Traces Workload Tests
##########################################################################

class TracesWorkloadTests(unittest.TestCase):
    """
    Test the manual workload traces methodology
    """

    def test_workload(self):
        """
        Test the workload generating work in simulation
        """

        sim = get_mock_simulation()
        sim.env = simpy.Environment()

        sim.replicas = [
            get_mock_replica(sim, id="r0", location=Location.HOME),
            get_mock_replica(sim, id="r1", location=Location.MOBILE),
        ]

        # set up the access tracking
        for replica in sim.replicas:
            replica.read = AccessTracking(sim.env)
            replica.write = AccessTracking(sim.env)

        work = TracesWorkload(TRACES, sim)
        sim.env.run(until=2000)

        writes = sum(replica.write.call_count for replica in sim.replicas)
        reads = sum(replica.read.call_count for replica in sim.replicas)
        self.assertEqual(reads, 6)
        self.assertEqual(writes, 12)

        devices = {device.id: device for device in sim.replicas}

        for access in work.reader:
            device = devices[access.replica]
            method = None

            if access.method == READ:
                method = device.read

            if access.method == WRITE:
                method = device.write

            self.assertIn(access.timestep, method.history)
            method.mock.assert_any_call(access.object)
