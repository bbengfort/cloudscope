# tests.test_simulation.test_workload.test_mobile
# Test the workload traces generation utility.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Mar 07 17:08:36 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_mobile.py [] benjamin@bengfort.com $

"""
Test the workload traces generation utility.
"""

##########################################################################
## Imports
##########################################################################

import simpy
import random
import unittest

try:
    from unittest import mock
except ImportError:
    import mock


from cloudscope.dynamo import CharacterSequence
from cloudscope.replica import Location, Device
from cloudscope.simulation.workload import MobileWorkload
from tests.test_simulation import get_mock_simulation, get_mock_replica
from cloudscope.exceptions import WorkloadException

##########################################################################
## Workload Tests
##########################################################################

class MobileWorkloadTests(unittest.TestCase):

    def setUp(self):
        """
        Rest the workload counter
        """
        MobileWorkload.counter.reset()

    def test_name(self):
        """
        Test the workload name (as a user)
        """
        sim  = get_mock_simulation()
        work = MobileWorkload(sim, objects=['A', 'B', 'C'])

        self.assertEqual(work.name, "user 1")

    def test_locations(self):
        """
        Test the workload extracting locations from simulation
        """
        sim = get_mock_simulation()

        sim.replicas = [
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE)
        ]

        work = MobileWorkload(sim, objects=['A', 'B', 'C'])
        self.assertEqual(len(work.locations), 3)

        for loc, num in ((Location.HOME, 2), (Location.WORK, 2), (Location.MOBILE, 3)):
            self.assertEqual(len(work.locations[loc]), num)

    def test_workload(self):
        """
        Test the workload generating work in simulation
        """

        sim = get_mock_simulation()
        sim.env = simpy.Environment()

        sim.replicas = [
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE)
        ]

        work = MobileWorkloadTests(
            sim, move_prob=1.0, switch_prob=1.0, read_prob=0.5,
            access_mean=20, access_stddev=4, objects=["A", "B", "C", "D", "E"]
        )

        env.run(until=1000)

        calls = sum(replica.write.call_count for replica in sim.replicas)
        calls += sum(replica.read.call_count for replica in sim.replicas)
        self.assertGreater(calls, 25)

    @unittest.skip("Belongs in the multi-workload generator")
    def test_objects_int(self):
        """
        Ensure multi-object workload can be initialized with int
        """
        sim  = get_mock_simulation()
        work = MobileWorkload(sim, objects=20)

        self.assertEqual(len(work.objects), 20)
        self.assertEqual(work.objects, tuple([
            char for char in CharacterSequence(limit="U", upper=True)
        ]))

    def test_objects_list(self):
        """
        Ensure multi-objects workload can be initialized with a list
        """
        sim  = get_mock_simulation()
        work = MobileWorkload(sim, objects=[
            "foo", "bar", "baz", "qux", "zoo",
        ])

        self.assertEqual(len(work.objects), 5)
        self.assertEqual(work.objects, [
            "foo", "bar", "baz", "qux", "zoo",
        ])

    def test_open_multi_object(self):
        """
        Test opening an multiple objects from a blank slate
        """
        sim = get_mock_simulation()

        sim.replicas = [
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE)
        ]

        work = MobileWorkload(sim, objects=["A", "B", "C", "D", "E"])
        self.assertEqual(len(work.objects), 5)
        self.assertEqual(work.objects, ["A", "B", "C", "D", "E"])

        self.assertIsNotNone(work.location)
        self.assertIsNotNone(work.device)
        self.assertIsNotNone(work.current)

        for idx in xrange(500):
            work.update()
            self.assertIsNotNone(work.current)
            self.assertEqual(len(work.objects), 5)
            self.assertLessEqual(len(filter(None, work.objects)), 5)

    def test_workload(self):
        """
        Test the multi-object workload generating work in simulation
        """

        sim = get_mock_simulation()
        sim.env = simpy.Environment()

        sim.replicas = [
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.HOME),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.WORK),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE),
            get_mock_replica(sim, location=Location.MOBILE)
        ]

        work = MobileWorkload(
            sim, move_prob=1.0, switch_prob=1.0, read_prob=0.5,
            access_mean=20, access_stddev=4, object_prob=0.5,
            objects=["A", "B", "C", "D", "E"]
        )

        sim.env.run(until=1000)

        calls = sum(replica.write.call_count for replica in sim.replicas)
        calls += sum(replica.read.call_count for replica in sim.replicas)
        self.assertGreater(calls, 25)
