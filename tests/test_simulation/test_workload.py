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

from cloudscope.replica.store import Version
from cloudscope.dynamo import CharacterSequence
from cloudscope.simulation.workload import Workload
from cloudscope.exceptions import ImproperlyConfigured
from cloudscope.simulation.workload import MultiVersionWorkload
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
## Multi Version Workload Tests
##########################################################################

class MultiVersionWorkloadTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        MultiVersionWorkload.reset()

    def test_versions_int(self):
        """
        Ensure multi-version workload can be initialized with int
        """
        sim  = get_mock_simulation()
        work = MultiVersionWorkload(sim.env, sim, versions=20)

        self.assertEqual(len(work.versions), 20)
        self.assertEqual(work.versions, [None for _ in xrange(20)])
        self.assertEqual(work.max_objs, len(work.versions))

    def test_versions_list(self):
        """
        Ensure multi-version workload can be initialized with a list
        """
        sim  = get_mock_simulation()
        work = MultiVersionWorkload(sim.env, sim, versions=[
            Version.new(x)(random.choice(sim.replicas))
            for x in CharacterSequence(limit="k", upper=True)
        ])

        self.assertEqual(len(work.versions), 10)
        for vers in work.versions:
            self.assertIsInstance(vers, Version)

        self.assertEqual(work.max_objs, len(work.versions))

    def test_multiple_versions_list(self):
        """
        Ensure a many instances of multi-version workload have same versions
        """

        sim  = get_mock_simulation()
        vers = [
            Version.new(x)(random.choice(sim.replicas))
            for x in CharacterSequence(limit="k", upper=True)
        ]

        for idx in xrange(20):
            work = MultiVersionWorkload(sim.env, sim, versions=vers)

            self.assertEqual(len(work.versions), 10)
            for idx, version in enumerate(work.versions):
                self.assertIsInstance(version, Version)
                self.assertIs(vers[idx], version)

            self.assertEqual(work.max_objs, len(work.versions))

    def test_int_then_list_versions(self):
        """
        Test setting a workload int, then workload versions
        """

        sim   = get_mock_simulation()
        vers  = [
            Version.new(x)(random.choice(sim.replicas))
            for x in CharacterSequence(limit="k", upper=True)
        ]

        worka = MultiVersionWorkload(sim.env, sim, versions=len(vers))
        self.assertEqual(len(worka.versions), len(vers))
        self.assertEqual(worka.versions, [None for _ in xrange(len(vers))])
        self.assertEqual(worka.max_objs, len(worka.versions))

        workb = MultiVersionWorkload(sim.env, sim, versions=vers)
        self.assertEqual(len(worka.versions), len(vers))
        self.assertEqual(len(workb.versions), len(vers))
        self.assertEqual(worka.versions, vers)
        self.assertEqual(workb.versions, vers)
        self.assertEqual(worka.max_objs, len(worka.versions))
        self.assertEqual(workb.max_objs, len(workb.versions))

    def test_bad_reconfigure_versions(self):
        """
        Assert that trying to merge two lists doesn't work
        """

        sim   = get_mock_simulation()
        vers  = [
            Version.new(x)(random.choice(sim.replicas))
            for x in CharacterSequence(limit="k", upper=True)
        ]

        worka = MultiVersionWorkload(sim.env, sim, versions=4)
        self.assertEqual(len(worka.versions), 4)
        self.assertEqual(worka.versions, [None for _ in xrange(4)])
        self.assertEqual(worka.max_objs, len(worka.versions))

        with self.assertRaises(ImproperlyConfigured):
            workb = MultiVersionWorkload(sim.env, sim, versions=vers)

    def test_int_then_bigger_int_versions(self):
        """
        Test setting a workload int, then extending with a bigger int
        """

        sim   = get_mock_simulation()
        vers  = [
            Version.new(x)(random.choice(sim.replicas))
            for x in CharacterSequence(limit="k", upper=True)
        ]

        worka = MultiVersionWorkload(sim.env, sim, versions=4)
        self.assertEqual(len(worka.versions), 4)
        self.assertEqual(worka.versions, [None for _ in xrange(4)])
        self.assertEqual(worka.max_objs, len(worka.versions))

        workb = MultiVersionWorkload(sim.env, sim, versions=len(vers))
        self.assertEqual(len(worka.versions), len(vers))
        self.assertEqual(len(workb.versions), len(vers))
        self.assertEqual(worka.versions, [None for _ in xrange(len(vers))])
        self.assertEqual(workb.versions, [None for _ in xrange(len(vers))])
        self.assertEqual(worka.max_objs, 4) # Note max objs doesn't change!
        self.assertEqual(workb.max_objs, len(workb.versions))

        worka.sync_versions(vers)
        self.assertEqual(len(worka.versions), len(vers))
        self.assertEqual(len(workb.versions), len(vers))
        self.assertEqual(worka.versions, vers)
        self.assertEqual(workb.versions, vers)
        self.assertEqual(worka.max_objs, 4)
        self.assertEqual(workb.max_objs, len(workb.versions))

    def test_open_single_object(self):
        """
        Test opening an object when there is only a single one
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

        work = MultiVersionWorkload(sim.env, sim, versions=1)
        self.assertEqual(len(work.versions), 1)
        self.assertEqual(work.versions, [None])
        self.assertEqual(work.max_objs, len(work.versions))

        work.move()
        self.assertIsNotNone(work.location)

        work.switch()
        self.assertIsNotNone(work.device)

        work.open()
        self.assertIsNotNone(work.current)

        self.assertEqual(len(work.versions), 1)
        self.assertIsNotNone(work.versions[0])
        self.assertIsInstance(work.versions[0], Version)

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

        work = MultiVersionWorkload(sim.env, sim, versions=5)
        self.assertEqual(len(work.versions), 5)
        self.assertEqual(work.versions, [None, None, None, None, None])
        self.assertEqual(work.max_objs, len(work.versions))

        work.move()
        self.assertIsNotNone(work.location)

        work.switch()
        self.assertIsNotNone(work.device)

        for idx in xrange(5):
            work.open()
            self.assertIsNotNone(work.current)
            self.assertEqual(len(work.versions), 5)
            self.assertLessEqual(len(filter(None, work.versions)), idx+1)


        for idx in xrange(1000):
            work.open()

        self.assertLessEqual(len(filter(None, work.versions)), 5)

        for idx in xrange(5):
            self.assertIsNotNone(work.versions[idx])
            self.assertIsInstance(work.versions[idx], Version)
