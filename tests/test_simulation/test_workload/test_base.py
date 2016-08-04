# tests.test_simulation.test_workload.test_base
# Tests for the base workload interface in CloudScope
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Aug 01 18:32:13 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_base.py [] benjamin@bengfort.com $

"""
Tests for the base workload interface in CloudScope
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

from cloudscope.simulation.workload.base import *
from tests.test_simulation.test_workload import AccessTracking
from tests.test_simulation import get_mock_simulation, get_mock_replica

from collections import Counter


##########################################################################
## Test Workload Base
##########################################################################

class WorkloadBaseTests(unittest.TestCase):
    """
    Test the base Workload object and workload API
    """

    klass   = Workload
    objects = ["A", "B", "C"]

    def setUp(self):
        """
        Sets up the environment and the workload class.
        """
        sim = get_mock_simulation()
        sim.env = simpy.Environment()
        device  = random.choice(sim.replicas)

        self.klass.counter.reset()
        self.work = self.klass(sim, device=device, objects=self.objects)

    def test_init(self):
        """
        Assert that by default init doesn't modify the state
        """
        self.assertIsNotNone(self.work.sim)
        self.assertIsNotNone(self.work.device)
        self.assertIsNotNone(self.work.location)
        self.assertIsNotNone(self.work.objects)
        self.assertIsNone(self.work.current)
        self.assertFalse(self.work.extra)

    def test_name(self):
        """
        Test the name of the workload for logging.
        """
        self.assertEqual(self.work.name, "user 1")

    def test_update(self):
        """
        Test that update is called at least once.
        """
        try:
            self.work.update()
        except Exception as e:
            self.fail("Calling updated resulted in exception: {}".format(e))

    def test_wait(self):
        """
        Test that the wait method is an interface
        """
        with self.assertRaises(NotImplementedError):
            self.work.wait()

    def test_access(self):
        """
        Test that the access method is an interface
        """
        with self.assertRaises(NotImplementedError):
            self.work.access()

    def test_workload(self):
        """
        Mock the workload API methods and run.
        """

        self.work.update = mock.MagicMock()
        self.work.wait   = mock.MagicMock(return_value=10)
        self.work.access = mock.MagicMock()

        self.work.sim.env.run(until=101 )

        self.assertEqual(self.work.update.call_count, 10)
        self.assertEqual(self.work.wait.call_count, 11)
        self.assertEqual(self.work.access.call_count, 10)


##########################################################################
## Test Routine Workload
##########################################################################

class RoutineWorkloadTests(WorkloadBaseTests):

    klass   = RoutineWorkload

    def test_init(self):
        """
        Assert that by default routine workload update at init
        """
        self.assertIsNotNone(self.work.sim)
        self.assertIsNotNone(self.work.device)
        self.assertIsNotNone(self.work.location)
        self.assertIsNotNone(self.work.objects)
        self.assertIsNotNone(self.work.current)
        self.assertFalse(self.work.extra)

    def test_access(self):
        """
        Test that the access method returns a value
        """
        # TODO: Do a better job of testing this!
        self.assertIsNotNone(self.work.access())

    def test_wait(self):
        """
        Test that the wait method works on a routine workload
        """
        for _ in range(1000):
            # Test bounded normal distribution
            wait = self.work.wait()
            self.assertGreater(wait, 1)

    def test_update(self):
        """
        Test updates of the current object on the routine workload
        """
        counts = Counter()
        for _ in range(1000):
            counts[self.work.current] += 1
            self.work.update()

        self.assertEqual(len(counts), 3)
