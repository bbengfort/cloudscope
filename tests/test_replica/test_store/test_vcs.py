# tests.test_store.test_vcs
# Tests the store functionality in the simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 12:40:47 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_vcs.py [] benjamin@bengfort.com $

"""
Tests the store functionality in the simulation.
"""

##########################################################################
## Imports
##########################################################################

import unittest
import random

from cloudscope.dynamo import Sequence
from cloudscope.replica import Replica, Version
from cloudscope.replica.store import ObjectFactory

try:
    from unittest import mock
except ImportError:
    import mock


##########################################################################
## Object Factory Tests
##########################################################################

class ObjectFactoryTests(unittest.TestCase):

    def test_object_factory(self):
        """
        Test the object factory method.
        """

        factory = ObjectFactory()
        sim = mock.MagicMock()

        # Test One
        A = factory()
        self.assertTrue(issubclass(A, Version))
        self.assertEqual(A(sim).name, "A")

        # Test Two
        B = factory()
        self.assertTrue(issubclass(B, Version))
        self.assertEqual(B(sim).name, "B")

        # Test Three
        C = factory()
        self.assertTrue(issubclass(C, Version))
        self.assertEqual(C(sim).name, "C")

##########################################################################
## Version Tests
##########################################################################

class VersionTests(unittest.TestCase):

    def setUp(self):
        self.sim = mock.MagicMock()
        self.sim.env.now  = 23
        self.sim.replicas = [Replica(self.sim) for x in xrange(5)]
        self.replica = random.choice(self.sim.replicas)

    def tearDown(self):
        self.sim = None
        self.replica = None

        # Reset the version counter
        Version.counter.reset()

    def test_nextv(self):
        """
        Test getting the next version of an object.
        """
        v1 = Version(self.replica)
        self.sim.env.now = 42
        v2 = v1.nextv(random.choice([r for r in self.sim.replicas if r != self.replica]))

        self.assertIsInstance(v2, Version)
        self.assertEqual(v2.parent, v1)
        self.assertEqual(v1.level, v2.level)
        self.assertFalse(v2.committed)
        self.assertGreater(v2.version, v1.version)
        self.assertGreater(v2.created, v1.created)
        self.assertGreater(v2.updated, v1.created)
        self.assertNotEqual(v2.writer, v1.writer)

        self.assertEqual(v1.counter, v2.counter)

    def test_update(self):
        """
        Test the update of a version over time.
        """
        v1 = Version(self.replica)

        for idx, replica in enumerate(self.sim.replicas):
            if replica == self.replica: continue

            self.sim.env.now += (2*(idx+1))
            v1.update(replica)
            self.assertGreater(v1.updated, v1.created)
            self.assertEqual(v1.updated, self.sim.env.now)

        # Check that this is the last call
        self.sim.results.update.assert_called_with(
            'visibility latency', (self.replica.id, str(v1), v1.created, v1.updated)
        )

        self.assertTrue(v1.is_visible())

    def test_visibility_metric(self):
        """
        Test that the visibility metric is tracked
        """
        v1 = Version(self.replica)

        calls = []
        replicas = [
            r for r in self.sim.replicas if r!= self.replica
        ]

        for idx, replica in enumerate(replicas):

            self.sim.env.now += (2*(idx+1))
            v1.update(replica)

            self.assertGreater(v1.updated, v1.created)
            self.assertEqual(v1.updated, self.sim.env.now)

            pcent = float(idx+2) / float(len(self.sim.replicas))
            calls.append(
                mock.call('visibility', (str(v1), pcent, v1.created, self.sim.env.now))
            )

        # Check that this is the last call
        self.sim.results.update.assert_has_calls(calls + [
            mock.call('visibility latency', (self.replica.id, str(v1), v1.created, v1.updated))
        ], any_order=True)

        self.assertTrue(v1.is_visible())

    def test_commit(self):
        """
        Test the commit of a version over time.
        """
        v1 = Version(self.replica)

        for idx, replica in enumerate(self.sim.replicas):
            if replica == self.replica: continue
            self.sim.env.now += (2*(idx+1))
            v1.update(replica)

        self.sim.results.update.assert_called_with(
            'visibility latency', (self.replica.id, str(v1), v1.created, v1.updated)
        )

        self.assertTrue(v1.is_visible())

        v1.update(self.replica, commit=True)
        self.assertTrue(v1.committed)
        self.assertTrue(v1.is_committed())

        self.sim.results.update.assert_called_with(
            'commit latency', (self.replica.id, str(v1), v1.created, v1.updated)
        )

    def test_is_stale(self):
        """
        Test the staleness of a version.
        """
        v1 = Version(self.replica)
        self.assertFalse(v1.is_stale())

        self.sim.env.now = 42
        v2 = v1.nextv(random.choice([r for r in self.sim.replicas if r != self.replica]))
        self.assertTrue(v1.is_stale())
        self.assertFalse(v2.is_stale())

    def test_version_comparison(self):
        """
        Test version comparison based on fork
        """

        v1 = Version(self.replica)
        v2 = v1.nextv(self.replica)

        self.assertLess(v1, v2)
        self.assertLessEqual(v1, v2)
        self.assertLessEqual(v2, v2)
        self.assertEqual(v1, v1)
        self.assertNotEqual(v1, v2)
        self.assertGreater(v2, v1)
        self.assertGreaterEqual(v2, v1)
        self.assertGreaterEqual(v2, v2)

    def test_version_string(self):
        """
        Test that the version string is compressed.
        """
        version = Version(self.replica)

        self.assertEqual(str(version), "root->1")

        for idx in xrange(100):
            version = version.nextv(self.replica)

        self.assertEqual(str(version), "100->101")

    @unittest.skip("Not implemented correctly yet.")
    def test_forked_version_string(self):
        """
        Test the compressability of a forked version string.
        """
        version = Version(self.replica)

        for idx in xrange(5):
            version = version.nextv(self.replica)

        # Now we split
        version_a = version.nextv(self.replica)
        version_b = version.nextv(self.replica)

        for idx in xrange(3):
            version_a = version_a.nextv(self.replica)

        for idx in xrange(9):
            version_b = version_b.nextv(self.replica)

        self.assertEqual(str(version_a), '')
        self.assertEqual(str(version_b), '')


class MultiVersionTests(unittest.TestCase):
    """
    Test the `new` version class constructor
    """

    def setUp(self):
        self.sim = mock.MagicMock()
        self.sim.env.now  = 23
        self.sim.replicas = [Replica(self.sim) for x in xrange(5)]
        self.replica = random.choice(self.sim.replicas)

    def tearDown(self):
        self.sim = None
        self.replica = None

    def test_new(self):
        """
        Test the version class creation mechanism
        """
        A = Version.new('A')
        B = Version.new('B')

        a = A(self.replica)
        b = B(self.replica)

        self.assertIsInstance(a, Version)
        self.assertIsInstance(b, Version)
        self.assertNotEqual(type(a), type(b))
        self.assertNotEqual(a.counter, b.counter)

        C = A.new('C')
        c = C(self.replica)

        self.assertIsInstance(c, Version)
        self.assertNotEqual(type(a), type(c))
        self.assertNotEqual(a.counter, c.counter)

    def test_fork(self):
        """
        Test the forking of multiple versions.
        """
        other = random.choice([r for r in self.sim.replicas if r != self.replica])

        A = Version.new('A')
        a1 = A(self.replica)
        self.sim.env.now += 10
        a2 = a1.nextv(other)

        self.sim.env.now += 10
        B = Version.new('B')
        b1 = B(other)

        self.sim.env.now += 10
        b2 = b1.nextv(self.replica)

        self.assertIsInstance(a2, A)
        self.assertIsInstance(b2, B)

        self.assertEqual(b2.parent, b1)
        self.assertEqual(a2.parent, a1)

        # This is kind of strange, but we're saying that the b2 and a2
        # parents are equivalent versions (e.g. root->1), then we test that
        # they're different objects with the ID method.
        self.assertEqual(b2.parent, a1)
        self.assertEqual(a2.parent, b1)
        self.assertIsNot(b2.parent, a1)
        self.assertIsNot(a2.parent, b1)

        self.assertGreater(a2.version, a1.version)
        self.assertGreater(b2.version, b1.version)
        self.assertEqual(a1.version, b1.version)
        self.assertEqual(a2.version, b2.version)

        self.assertGreater(a2.created, a1.created)
        self.assertGreater(b1.created, a2.created)
        self.assertGreater(b2.created, b1.created)

    def test_update(self):
        """
        Test the update of multiple versions over time.
        """
        A = Version.new('A')
        a = A(self.replica)
        B = Version.new('B')
        b = B(self.replica)

        calls = []
        replicas = [
            r for r in self.sim.replicas if r != self.replica
        ]

        for idx, replica in enumerate(replicas):

            self.sim.env.now += (2*(idx+1))
            a.update(replica)
            b.update(replica)

            pcent = float(idx+2) / float(len(self.sim.replicas))
            calls.append(mock.call('visibility', (str(a), pcent, a.created, self.sim.env.now)))
            calls.append(mock.call('visibility', (str(b), pcent, a.created, self.sim.env.now)))

            self.assertGreater(a.updated, a.created)
            self.assertEqual(a.updated, self.sim.env.now)
            self.assertGreater(b.updated, b.created)
            self.assertEqual(b.updated, self.sim.env.now)

        self.sim.results.update.assert_has_calls(calls + [
            mock.call('visibility latency', (self.replica.id, str(a), a.created, a.updated)),
            mock.call('visibility latency', (self.replica.id, str(b), b.created, b.updated)),
        ], any_order=True)

        self.assertTrue(a.is_visible())
        self.assertTrue(b.is_visible())

    def test_commit(self):
        """
        Test the commit of multiple versions over time.
        """
        A = Version.new('A')
        a = A(self.replica)
        B = Version.new('B')
        b = B(self.replica)

        for idx, replica in enumerate(self.sim.replicas):
            if replica == self.replica: continue

            self.sim.env.now += (2*(idx+1))
            a.update(replica)
            b.update(replica)

        a.update(self.replica, commit=True)
        self.assertTrue(a.committed)
        self.assertTrue(a.is_committed())
        self.assertFalse(b.committed)
        self.assertFalse(b.is_committed())

        self.sim.results.update.assert_called_with(
            'commit latency', (self.replica.id, str(a), a.created, a.updated)
        )

        b.update(self.replica, commit=True)
        self.assertTrue(a.committed)
        self.assertTrue(a.is_committed())
        self.assertTrue(b.committed)
        self.assertTrue(b.is_committed())

        self.sim.results.update.assert_called_with(
            'commit latency', (self.replica.id, str(b), b.created, b.updated)
        )

    def test_is_stale(self):
        """
        Test the staleness of multiple versions.
        """
        A = Version.new('A')
        a = A(self.replica)
        B = Version.new('B')
        b = B(self.replica)

        self.assertFalse(a.is_stale())
        self.assertFalse(b.is_stale())

        self.sim.env.now += 42
        b2 = b.nextv(self.replica)
        self.assertTrue(b.is_stale())
        self.assertFalse(a.is_stale())
        self.assertFalse(b2.is_stale())

        self.sim.env.now += 42
        a2 = a.nextv(self.replica)
        self.assertTrue(a.is_stale())
        self.assertTrue(b.is_stale())
        self.assertFalse(a2.is_stale())
        self.assertFalse(b2.is_stale())

    def test_is_forked(self):
        """
        Test the fork detection mechanism of multiple versions.
        """
        # Create new version history for an object named A
        A = Version.new('A')

        # Create the first version
        a1 = A(self.replica)
        self.assertFalse(a1.is_forked())

        # Create another version
        a2 = a1.nextv(self.replica)
        self.assertFalse(a1.is_forked())
        self.assertFalse(a2.is_forked())

        # Create a fork!
        a3 = a1.nextv(self.replica)
        self.assertTrue(a1.is_forked())
        self.assertFalse(a2.is_forked())
        self.assertFalse(a3.is_forked())

        # Create another version from a2
        a4 = a2.nextv(self.replica)
        self.assertTrue(a1.is_forked())
        self.assertFalse(a2.is_forked())
        self.assertFalse(a3.is_forked())
        self.assertFalse(a4.is_forked())

        # Create a fork from a2!
        a5 = a2.nextv(self.replica)
        self.assertTrue(a1.is_forked())
        self.assertTrue(a2.is_forked())
        self.assertFalse(a3.is_forked())
        self.assertFalse(a4.is_forked())
        self.assertFalse(a5.is_forked())

        # Create another fork from a1!
        a6 = a1.nextv(self.replica)
        self.assertTrue(a1.is_forked())
        self.assertTrue(a2.is_forked())
        self.assertFalse(a3.is_forked())
        self.assertFalse(a4.is_forked())
        self.assertFalse(a5.is_forked())
        self.assertFalse(a6.is_forked())

    def test_unforking(self):
        """
        Test "unforking" a version by dropping the child access.
        """
        # Create new version history for an object named A
        A = Version.new('A')

        # Create the first version
        a1 = A(self.replica)
        self.assertFalse(a1.is_forked())

        # Create another version
        a2 = a1.nextv(self.replica)
        self.assertFalse(a1.is_forked())
        self.assertFalse(a2.is_forked())

        # Create a fork!
        a3 = a1.nextv(self.replica)
        self.assertTrue(a1.is_forked())
        self.assertFalse(a2.is_forked())
        self.assertFalse(a3.is_forked())

        # Now drop a3 and "unfork" it.
        a3.access.drop()
        self.assertFalse(a1.is_forked())
        self.assertFalse(a2.is_forked())
        self.assertFalse(a3.is_forked())

        # Create two more forks!
        a4 = a1.nextv(self.replica)
        a5 = a1.nextv(self.replica)
        self.assertTrue(a1.is_forked())
        self.assertFalse(a2.is_forked())
        self.assertFalse(a3.is_forked())
        self.assertFalse(a4.is_forked())
        self.assertFalse(a5.is_forked())

        # Drop a4 but a1 remains forked
        a4.access.drop()
        self.assertTrue(a1.is_forked())

        # Drop a5 which unforks a1
        a5.access.drop()
        self.assertFalse(a1.is_forked())

    def test_version_comparison(self):
        """
        Test multiple versions comparison based on fork
        """
        A = Version.new('A')
        a1 = A(self.replica)
        a2 = a1.nextv(self.replica)
        B = Version.new('B')
        b1 = B(self.replica)
        b2 = b1.nextv(self.replica)

        self.assertLess(a1, a2)
        self.assertLess(b1, b2)
        self.assertLess(b1, a2)
        self.assertLess(a1, b2)

        self.assertLessEqual(a1, a2)
        self.assertLessEqual(b1, b2)
        self.assertLessEqual(b1, a2)
        self.assertLessEqual(a1, b2)
        self.assertLessEqual(a1, b1)
        self.assertLessEqual(a2, b2)

        self.assertEqual(a1, b1)
        self.assertEqual(a2, b2)
        self.assertIsNot(a1, b1)
        self.assertIsNot(a2, b2)

        self.assertNotEqual(a1, b2)
        self.assertNotEqual(b1, a2)
        self.assertNotEqual(a1, a2)
        self.assertNotEqual(b1, b2)

        self.assertGreater(a2, a1)
        self.assertGreater(b2, b1)
        self.assertGreater(a2, b1)
        self.assertGreater(b2, a1)

        self.assertGreaterEqual(a2, a1)
        self.assertGreaterEqual(b2, b1)
        self.assertGreaterEqual(a2, b1)
        self.assertGreaterEqual(b2, a1)
        self.assertGreaterEqual(b2, a2)
        self.assertGreaterEqual(b1, a1)

    def test_version_string(self):
        """
        Test that multiple versions string is accurate.
        """
        A = Version.new('A')
        a = A(self.replica)
        B = Version.new('B')
        b = B(self.replica)

        self.assertEqual(str(a), "root->A.1")
        self.assertEqual(str(b), "root->B.1")

        for idx in xrange(100):
            a = a.nextv(self.replica)
            b = b.nextv(self.replica)

        self.assertEqual(str(a), "A.100->A.101")
        self.assertEqual(str(b), "B.100->B.101")
