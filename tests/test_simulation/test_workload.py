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

import random
import unittest

try:
    from unittest import mock
except ImportError:
    import mock


from cloudscope.dynamo import CharacterSequence
from cloudscope.simulation.workload import Workload
from cloudscope.simulation.workload import MultiObjectWorkload
from tests.test_simulation import get_mock_simulation, get_mock_replica


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

        print sim.replicas

        work = Workload(sim.env, sim)
        self.assertEqual(len(work.locations), 3)

        for loc, num in (('home', 2), ('work', 2), ('mobile', 3)):
            self.assertEqual(len(work.locations[loc]), num)

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
        self.assertEqual(work.objects, frozenset([
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
        self.assertEqual(work.objects, frozenset([
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
        self.assertEqual(work.objects, frozenset(["A", "B", "C", "D", "E"]))

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
