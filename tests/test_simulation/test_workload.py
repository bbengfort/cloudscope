# tests.test_simulation.test_workload
# Test the workload traces generation utility.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Mar 07 17:08:36 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_workload.py [] benjamin@bengfort.com $

"""
Test the workload traces generation utility.
"""

##########################################################################
## Imports
##########################################################################

import os
import simpy
import random
import unittest

try:
    from unittest import mock
except ImportError:
    import mock


from cloudscope.dynamo import CharacterSequence
from cloudscope.simulation.workload import Workload
from cloudscope.simulation.workload import MultiObjectWorkload
from cloudscope.simulation.workload import Access, TracesWorkload, READ, WRITE
from tests.test_simulation import get_mock_simulation, get_mock_replica
from cloudscope.exceptions import WorkloadException

##########################################################################
## Workload Tests
##########################################################################

class WorkloadTests(unittest.TestCase):

    def setUp(self):
        Workload.counter.reset()

    def test_name(self):
        """
        Test the workload name (as a user)
        """
        sim  = get_mock_simulation()
        work = Workload(sim.env, sim)

        self.assertEqual(work.name, "user 1")

    def test_locations(self):
        """
        Test the workload extracting locations from simulation
        """
        sim = get_mock_simulation()

        sim.replicas = [
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile")
        ]

        work = Workload(sim.env, sim)
        self.assertEqual(len(work.locations), 3)

        for loc, num in (('home', 2), ('work', 2), ('mobile', 3)):
            self.assertEqual(len(work.locations[loc]), num)

    def test_workload(self):
        """
        Test the workload generating work in simulation
        """

        sim = get_mock_simulation()
        env = simpy.Environment()

        sim.replicas = [
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile")
        ]

        work = Workload(
            env, sim, move_prob=1.0, switch_prob=1.0, read_prob=0.5,
            access_mean=20, access_stddev=4
        )

        env.run(until=1000)

        calls = sum(replica.write.call_count for replica in sim.replicas)
        calls += sum(replica.read.call_count for replica in sim.replicas)
        self.assertGreater(calls, 25)

##########################################################################
## Multi Object Workload Tests
##########################################################################

class MultiObjectWorkloadTests(unittest.TestCase):

    def test_objects_int(self):
        """
        Ensure multi-object workload can be initialized with int
        """
        sim  = get_mock_simulation()
        work = MultiObjectWorkload(sim.env, sim, objects=20)

        self.assertEqual(len(work.objects), 20)
        self.assertEqual(work.objects, tuple([
            char for char in CharacterSequence(limit="U", upper=True)
        ]))

    def test_objects_list(self):
        """
        Ensure multi-objects workload can be initialized with a list
        """
        sim  = get_mock_simulation()
        work = MultiObjectWorkload(sim.env, sim, objects=[
            "foo", "bar", "baz", "qux", "zoo",
        ])

        self.assertEqual(len(work.objects), 5)
        self.assertEqual(work.objects, tuple([
            "foo", "bar", "baz", "qux", "zoo",
        ]))

    def test_open_multi_object(self):
        """
        Test opening an multiple objects from a blank slate
        """
        sim = get_mock_simulation()

        sim.replicas = [
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile")
        ]

        work = MultiObjectWorkload(sim.env, sim, objects=5)
        self.assertEqual(len(work.objects), 5)
        self.assertEqual(work.objects, tuple(["A", "B", "C", "D", "E"]))

        work.move()
        self.assertIsNotNone(work.location)

        work.switch()
        self.assertIsNotNone(work.device)

        self.assertIsNone(work.current)

        for idx in xrange(500):
            work.open()
            self.assertIsNotNone(work.current)
            self.assertEqual(len(work.objects), 5)
            self.assertLessEqual(len(filter(None, work.objects)), 5)

    def test_workload(self):
        """
        Test the multi-object workload generating work in simulation
        """

        sim = get_mock_simulation()
        env = simpy.Environment()

        sim.replicas = [
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="home"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="work"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile"),
            get_mock_replica(sim, location="mobile")
        ]

        work = MultiObjectWorkload(
            env, sim, move_prob=1.0, switch_prob=1.0, read_prob=0.5,
            access_mean=20, access_stddev=4, object_prob=0.5
        )

        env.run(until=1000)

        calls = sum(replica.write.call_count for replica in sim.replicas)
        calls += sum(replica.read.call_count for replica in sim.replicas)
        self.assertGreater(calls, 25)


##########################################################################
## Fixtures
##########################################################################

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")
TRACES   = os.path.join(FIXTURES, "traces.tsv")


##########################################################################
## Traces Workload Tests
##########################################################################

class TracesWorkloadTests(unittest.TestCase):
    """
    Test the manual workload traces methodology
    """

    def test_line_parsing(self):
        """
        Test that workload lines are parsed correctly
        """

        sim   = get_mock_simulation()
        work  = TracesWorkload(TRACES, sim.env, sim)
        value = work.parse("  53    r1  B   read  ")
        self.assertEqual(value, Access(53, "r1", "B", "read"))

        value = work.parse("2424.32 r9  write")
        self.assertEqual(value, Access(2424, "r9", None, "write"))

    def test_line_parse_failure(self):
        """
        Test that invalid lines raise an exception
        """
        sim   = get_mock_simulation()
        work  = TracesWorkload(TRACES, sim.env, sim)

        with self.assertRaises(WorkloadException):
            value = work.parse("abcdefg")

        with self.assertRaises(WorkloadException):
            value = work.parse("23  r2   A     touch")

        with self.assertRaises(WorkloadException):
            value = work.parse("")

    def test_traces_read(self):
        """
        Test that a traces fixture can be read and parsed
        """
        sim   = get_mock_simulation()
        work  = TracesWorkload(TRACES, sim.env, sim)
        count = 0

        for access in work.accesses():
            count += 1
            self.assertIsInstance(access, Access)

        self.assertEqual(count, 18)

    def test_workload(self):
        """
        Test the workload generating work in simulation
        """

        class AccessTracking(object):

            def __init__(self, env):
                self.env     = env
                self.mock    = mock.Mock()
                self.history = []

            def __call__(self, *args, **kwargs):
                self.history.append(self.env.now)
                self.mock(*args, **kwargs)

            @property
            def call_count(self):
                return self.mock.call_count


        sim = get_mock_simulation()
        env = simpy.Environment()

        sim.replicas = [
            get_mock_replica(sim, id="r0", location="home"),
            get_mock_replica(sim, id="r1", location="mobile"),
        ]

        # set up the access tracking
        for replica in sim.replicas:
            replica.read = AccessTracking(env)
            replica.write = AccessTracking(env)

        work = TracesWorkload(TRACES, env, sim)
        env.run(until=2000)

        writes = sum(replica.write.call_count for replica in sim.replicas)
        reads = sum(replica.read.call_count for replica in sim.replicas)
        self.assertEqual(reads, 6)
        self.assertEqual(writes, 12)

        devices = {device.id: device for device in sim.replicas}

        for access in work.accesses():
            device = devices[access.replica]
            method = None

            if access.method == READ:
                method = device.read

            if access.method == WRITE:
                method = device.write

            self.assertIn(access.timestep, method.history)
            method.mock.assert_any_call(access.object)
