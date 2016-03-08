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

    def test_versions_int(self):
        """
        Ensure multi version workload can be initialized with int
        """
        sim  = get_mock_simulation()
        work = MultiVersionWorkload(sim.env, sim, versions=20)

        self.assertEqual(len(work.versions), 20)
        self.assertEqual(work.versions, [None for _ in xrange(20)])

    def test_versions_list(self):
        """
        Ensure multi version workload can be initialized with a list
        """
        sim  = get_mock_simulation()
        work = MultiVersionWorkload(sim.env, sim, versions=[
            Version.new(x)(random.choice(sim.replicas))
            for x in CharacterSequence(limit="k", upper=True)
        ])

        self.assertEqual(len(work.versions), 10)
        for vers in work.versions:
            self.assertIsInstance(vers, Version)
            
