# tests.test_replica.test_access
# Tests the access events (e.g. read and write events).
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Apr 04 16:55:33 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_access.py [f37a55a] benjamin@bengfort.com $

"""
Tests the access events (e.g. read and write events).
"""

##########################################################################
## Imports
##########################################################################

import unittest
import random

from cloudscope.replica.access import *
from cloudscope.replica import Version, ObjectFactory
from tests.test_simulation import get_mock_simulation

try:
    from unittest import mock
except ImportError:
    import mock

# Set up the object factory
get_object = ObjectFactory()


##########################################################################
## Access Event Tests
##########################################################################

class AccessTests(unittest.TestCase):

    def setUp(self):
        self.File = get_object()
        self.name = self.File.__name__
        self.sim  = get_mock_simulation()
        self.replica = random.choice(self.sim.replicas)

    def test_create_access(self):
        """
        Test the access create class method
        """
        obja = Access.create(self.name, self.replica)
        self.assertIsInstance(obja, Access)

        objb = Access.create(obja, self.replica)
        self.assertIs(obja, objb)

    def test_access_latency(self):
        """
        Test the access latency functionality
        """
        self.assertEqual(self.sim.env.now, 42, "env.now not setup correctly!")
        access = Access(self.name, self.replica)

        # Move forward in time and check latency
        self.sim.env.now = 84
        self.assertIsNone(access.latency)
        access.update(self.File(self.replica), completed=True)

        self.assertTrue(access.is_completed())
        self.assertFalse(access.is_dropped())
        self.assertEqual(access.latency, 42)

    def test_access_is_completed(self):
        """
        Test the access event is completed functionality
        """
        access = Access(self.name, self.replica)

        # Access starts incomplete
        self.assertFalse(access.is_completed())

        # Access is incomplete even on version update
        result = access.update(self.File(self.replica))
        self.assertIs(result, access, "Access interaction methods must return self!")
        self.assertFalse(access.is_completed())

        # Access is complete after complete is called
        result = access.complete()
        self.assertIs(result, access, "Access interaction methods must return self!")
        self.assertTrue(access.is_completed())
        self.assertFalse(access.is_dropped())

    def test_dropping_access(self):
        """
        Test that accesses can be dropped
        """
        access = Access(self.name, self.replica)
        self.assertFalse(access.is_dropped())

        result = access.drop()
        self.assertIs(result, access, "Access interaction methods must return self!")

        self.assertTrue(access.is_dropped())
        self.assertFalse(access.is_completed())

    def test_drop_latency(self):
        """
        Test that the latency until drop can be measured
        """
        self.assertEqual(self.sim.env.now, 42, "env.now not setup correctly!")
        access = Access(self.name, self.replica)

        # Move forward in time and check latency
        self.sim.env.now = 84
        access.drop()

        self.assertTrue(access.is_dropped())
        self.assertFalse(access.is_completed())
        self.assertEqual(access.latency, 42)

    @unittest.skip("Temporarily removed this requirement for federated experiments")
    def test_only_complete_once(self):
        """
        Test calling access complete multiple times
        """
        access = Access(self.name, self.replica)
        version = self.File(self.replica)
        access.update(version)

        self.sim.env.now = 48
        self.assertFalse(access.is_completed())
        self.assertFalse(access.is_dropped())
        access.complete()
        self.assertTrue(access.is_completed())
        self.assertFalse(access.is_dropped())
        self.assertEqual(access.finished, 48)

        with self.assertRaises(AccessError):
            access.complete()

    def test_is_local_to(self):
        """
        Test the locality check on the access
        """
        local  = self.replica
        remote = self.replica

        while remote == local:
            remote = random.choice(self.sim.replicas)

        assert local != remote
        access = Access('foo', local)

        # Test the local locality
        self.assertTrue(access.is_local_to(local))
        self.assertFalse(access.is_local_to(remote))

        # Test the remote locality
        self.assertTrue(access.is_remote_to(remote))
        self.assertFalse(access.is_remote_to(local))

    def test_access_counts_by_id(self):
        """
        Test the autoincrement id feature of accesses
        """
        from itertools import count

        # Reset the class counters
        Access.counter = count()
        Read.counter = count()
        Write.counter = count()

        self.assertEqual(Access('A', self.replica).id, 0)
        self.assertEqual(Read('A', self.replica).id, 0)
        self.assertEqual(Write('A', self.replica).id, 0)

        self.assertEqual(Access('A', self.replica).id, 1)
        self.assertEqual(Write('A', self.replica).id, 1)
        self.assertEqual(Read('A', self.replica).id, 1)

        self.assertEqual(Access('A', self.replica).id, 2)
        self.assertEqual(Access('A', self.replica).id, 3)
        self.assertEqual(Write('A', self.replica).id, 2)
        self.assertEqual(Access('A', self.replica).id, 4)
        self.assertEqual(Read('A', self.replica).id, 2)
        self.assertEqual(Write('A', self.replica).id, 3)
        self.assertEqual(Read('A', self.replica).id, 3)
        self.assertEqual(Read('A', self.replica).id, 4)

##########################################################################
## Read Event Tests
##########################################################################

class ReadAccessTests(unittest.TestCase):

    def setUp(self):
        self.File = get_object()
        self.name = self.File.__name__
        self.sim  = get_mock_simulation()
        self.replica = random.choice(self.sim.replicas)

    def test_create_read(self):
        """
        Test the read create class method
        """
        obja = Read.create(self.name, self.replica)
        self.assertIsInstance(obja, Access)

        objb = Read.create(obja, self.replica)
        self.assertIs(obja, objb)

    def test_type_check(self):
        """
        Test the read access type checking
        """
        access = Read(self.name, self.replica)
        self.assertEqual(access.type, READ)

    @unittest.skip("vital test, but mock is not behaving!")
    def test_access_is_completed(self):
        """
        Test the read access event is completed without error
        """
        access = Read(self.name, self.replica)

        # Access starts incomplete
        self.assertFalse(access.is_completed())

        # Access is incomplete even on version update
        access.update(self.File(self.replica))
        self.assertFalse(access.is_completed())

        # Access is complete after complete is called
        access.complete()
        self.assertTrue(access.is_completed())
        self.assertFalse(access.is_dropped())

    def test_complete(self):
        pass


##########################################################################
## Write Event Tests
##########################################################################

class WriteAccessTests(unittest.TestCase):

    def setUp(self):
        self.File = get_object()
        self.name = self.File.__name__
        self.sim  = get_mock_simulation()
        self.replica = random.choice(self.sim.replicas)

    def test_create_write(self):
        """
        Test the write create class method
        """
        obja = Write.create(self.name, self.replica)
        self.assertIsInstance(obja, Access)

        objb = Write.create(obja, self.replica)
        self.assertIs(obja, objb)

    def test_type_check(self):
        """
        Test the write access type checking
        """
        access = Write(self.name, self.replica)
        self.assertEqual(access.type, WRITE)

    @unittest.skip("vital test, but mock is not behaving!")
    def test_access_is_completed(self):
        """
        Test the write access event is completed without error
        """
        access = Write(self.name, self.replica)

        # Access starts incomplete
        self.assertFalse(access.is_completed())

        # Access is incomplete even on version update
        access.update(self.File(self.replica))
        self.assertFalse(access.is_completed())

        # Access is complete after complete is called
        access.complete()
        self.assertTrue(access.is_completed())
        self.assertFalse(access.is_dropped())
