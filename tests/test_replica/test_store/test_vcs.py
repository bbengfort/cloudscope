# tests.test_store.test_vcs
# Tests the store functionality in the simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 12:40:47 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_vcs.py [2ab0a32] benjamin@bengfort.com $

"""
Tests the store functionality in the simulation.
"""

##########################################################################
## Imports
##########################################################################

import unittest
import random

from cloudscope.config import settings
from cloudscope.dynamo import Sequence
from cloudscope.replica.store import ObjectFactory
from cloudscope.replica.store.vcs import LamportScalar
from cloudscope.replica import Replica, State, Consistency
from cloudscope.replica import Version, LamportVersion, FederatedVersion
from cloudscope.exceptions import SimulationException

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
        replica = mock.MagicMock()

        # Test One
        A = factory()
        self.assertTrue(issubclass(A, Version))
        self.assertEqual(A(replica).name, "A")

        # Test Two
        B = factory()
        self.assertTrue(issubclass(B, Version))
        self.assertEqual(B(replica).name, "B")

        # Test Three
        C = factory()
        self.assertTrue(issubclass(C, Version))
        self.assertEqual(C(replica).name, "C")

    def test_object_factory_klass(self):
        """
        Test the object factory returns the correct class.
        """

        # Save the original setting
        orig = settings.simulation.versioning

        # Create the factory and the default replica
        factory = ObjectFactory()
        replica = mock.MagicMock()

        # Test the default versioning setting
        settings.simulation.versioning = 'default'
        A = factory()
        self.assertTrue(issubclass(A, Version))

        # Test the lamport versioning setting
        settings.simulation.versioning = 'lamport'
        B = factory()
        self.assertTrue(issubclass(B, Version))
        self.assertTrue(issubclass(B, LamportVersion))

        # Test the federated versioning setting
        settings.simulation.versioning = 'federated'
        C = factory()
        self.assertTrue(issubclass(C, Version))
        self.assertTrue(issubclass(C, FederatedVersion))

        # Add the original setting back
        settings.simulation.versioning = orig


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
                mock.call('visibility', (self.replica.id, str(v1), pcent, v1.created, self.sim.env.now))
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


##########################################################################
## Multi Version Tests
##########################################################################

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

    def test_replica_continuation(self):
        """
        Test the writing of multiple versions on different replicas
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
            calls.append(mock.call('visibility', (self.replica.id, str(a), pcent, a.created, self.sim.env.now)))
            calls.append(mock.call('visibility', (self.replica.id, str(b), pcent, a.created, self.sim.env.now)))

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


##########################################################################
## Version Subclass Tests
##########################################################################

class VersionSubclassCases(object):
    """
    These test cases ensure that subclasses of version behave as expected.
    These tests are essentially the same as the MultiVersionTests though some
    minor implementation details have been changed or adapted from the
    VersionTests cases as well. They are kept separate only so that I don't
    have to refactor, though I know I probably should.
    """

    klass = None

    def setUp(self):
        self.sim = mock.MagicMock()
        self.sim.env.now  = 38
        self.sim.replicas = [Replica(self.sim) for x in xrange(5)]
        self.replica = random.choice(self.sim.replicas)

    def tearDown(self):
        self.sim = None
        self.replica = None

        # Reset the version counter if the class has one
        try:
            self.counter.reset()
        except AttributeError:
            pass

    def shortDescription(self, *args, **kwargs):
        """
        Modifies the short description of subcases
        """
        descr = unittest.TestCase.shortDescription(self, *args, **kwargs)
        return descr.format(self.klass.__name__)

    def test_case(self):
        """
        Tests the {} case to make sure there is a subclass being tested!
        """
        if self.klass is None:
            self.fail(
                "Tests were run for the base cases, no subclass supplied"
            )

        if not issubclass(self.klass, Version):
            self.fail(
                "{} is not a subclass of {}".format(
                    repr(self.klass), repr(Version)
                )
            )

    def test_new(self):
        """
        Test the {} class creation mechanism
        """
        A = self.klass.new('A')
        B = self.klass.new('B')

        a = A(self.replica)
        b = B(self.replica)

        self.assertIsInstance(a, self.klass)
        self.assertIsInstance(b, self.klass)
        self.assertNotEqual(type(a), type(b))
        self.assertNotEqual(a.counter, b.counter)

        C = A.new('C')
        c = C(self.replica)

        self.assertIsInstance(c, self.klass)
        self.assertNotEqual(type(a), type(c))
        self.assertNotEqual(a.counter, c.counter)

    def test_increment_version(self):
        """
        Test the {} class increment version mechanism
        """
        Foo = self.klass.new('Foo')

        # Increasing version numbers for the same replica.
        v1 = Foo.increment_version(self.replica)
        self.assertEqual(v1, Foo.latest_version())

        v2 = Foo.increment_version(self.replica)
        self.assertGreater(v2, v1)
        self.assertEqual(v2, Foo.latest_version())

        v3 = Foo.increment_version(self.replica)
        self.assertGreater(v3, v1)
        self.assertGreater(v3, v2)
        self.assertEqual(v3, Foo.latest_version())

    def test_nextv(self):
        """
        Test getting the next {} of an object
        """
        v1 = self.klass(self.replica)
        self.sim.env.now = 42
        v2 = v1.nextv(random.choice([
                r for r in self.sim.replicas if r != self.replica
            ]))

        self.assertIsInstance(v2, self.klass)
        self.assertEqual(v2.parent, v1)
        self.assertEqual(v1.level, v2.level)

        self.assertFalse(v1.committed)
        self.assertFalse(v2.committed)

        self.assertGreater(v2.version, v1.version)
        self.assertGreater(v2.created, v1.created)
        self.assertGreater(v2.updated, v1.created)
        self.assertNotEqual(v2.writer, v1.writer)

        self.assertEqual(v1.counter, v2.counter)

    def test_single_update(self):
        """
        Test the update of a {} over time
        """
        v1 = self.klass(self.replica)

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

    def test_multiple_update(self):
        """
        Test the update of multiple {}s over time (and visibility metric)
        """
        A = self.klass.new('A')
        a = A(self.replica)
        B = self.klass.new('B')
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
            calls.append(mock.call('visibility', (self.replica.id, str(a), pcent, a.created, self.sim.env.now)))
            calls.append(mock.call('visibility', (self.replica.id, str(b), pcent, a.created, self.sim.env.now)))

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
        Test the commit of a {} over time
        """
        v1 = self.klass(self.replica)

        for idx, replica in enumerate(self.sim.replicas):
            if replica == self.replica: continue
            self.sim.env.now += (2*(idx+1))
            v1.update(replica)
            self.assertFalse(v1.committed)
            self.assertFalse(v1.is_committed())

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
        Test the staleness detection of multiple {}s
        """
        A = self.klass.new('A')
        B = self.klass.new('B')

        a1 = A(self.replica)
        b1 = B(self.replica)

        self.assertFalse(a1.is_stale())
        self.assertFalse(b1.is_stale())

        self.sim.env.now += 42

        b2 = b1.nextv(self.replica)
        self.assertTrue(b1.is_stale())
        self.assertFalse(b2.is_stale())
        self.assertFalse(a1.is_stale())

        self.sim.env.now += 42

        a2 = a1.nextv(self.replica)
        self.assertTrue(a1.is_stale())
        self.assertTrue(b1.is_stale())
        self.assertFalse(a2.is_stale())
        self.assertFalse(b2.is_stale())

    def test_replica_continuation(self):
        """
        Test the writing of multiple {}s on different replicas
        """
        alpha = self.replica
        bravo = random.choice([r for r in self.sim.replicas if r != alpha])

        Foo = self.klass.new('Foo')
        Bar = self.klass.new('Bar')

        f1 = Foo(alpha)
        self.sim.env.now += 10
        f2 = f1.nextv(bravo)

        self.sim.env.now += 10
        b1 = Bar(bravo)

        self.sim.env.now += 10
        b2 = b1.nextv(alpha)

        self.assertIsInstance(f2, Foo)
        self.assertIsInstance(b2, Bar)

        self.assertEqual(b2.parent, b1)
        self.assertEqual(f2.parent, f1)

        # This is kind of strange, but we're saying that the b2 and a2
        # parents are equivalent versions (e.g. root->1), then we test that
        # they're different objects with the ID method.
        self.assertEqual(b2.parent, f1)
        self.assertEqual(f2.parent, b1)
        self.assertIsNot(b2.parent, f1)
        self.assertIsNot(f2.parent, b1)

        self.assertGreater(f2.version, f1.version)
        self.assertGreater(b2.version, b1.version)
        self.assertEqual(f1.version, b1.version)
        self.assertEqual(f2.version, b2.version)

        self.assertGreater(f2.created, f1.created)
        self.assertGreater(b1.created, f2.created)
        self.assertGreater(b2.created, b1.created)

    def test_is_forked(self):
        """
        Test the fork detection method of a {} over time
        """
        A = self.klass.new('A')
        alpha = self.replica
        bravo = random.choice([r for r in self.sim.replicas if r != alpha])

        # Create the first version
        a1 = A(alpha)
        self.assertFalse(a1.is_forked())

        # Create another version
        a2 = a1.nextv(alpha)
        self.assertFalse(a1.is_forked())
        self.assertFalse(a2.is_forked())

        # Create a fork!
        a3 = a1.nextv(bravo)
        self.assertTrue(a1.is_forked())
        self.assertFalse(a2.is_forked())
        self.assertFalse(a3.is_forked())

        # Create another version from a2
        a4 = a2.nextv(bravo)
        self.assertTrue(a1.is_forked())
        self.assertFalse(a2.is_forked())
        self.assertFalse(a3.is_forked())
        self.assertFalse(a4.is_forked())

        # Create a fork from a2!
        a5 = a2.nextv(alpha)
        self.assertTrue(a1.is_forked())
        self.assertTrue(a2.is_forked())
        self.assertFalse(a3.is_forked())
        self.assertFalse(a4.is_forked())
        self.assertFalse(a5.is_forked())

        # Create another fork from a1!
        a6 = a1.nextv(bravo)
        self.assertTrue(a1.is_forked())
        self.assertTrue(a2.is_forked())
        self.assertFalse(a3.is_forked())
        self.assertFalse(a4.is_forked())
        self.assertFalse(a5.is_forked())
        self.assertFalse(a6.is_forked())

    def test_unforking(self):
        """
        Test "unforking" a {} by dropping the child access
        """
        # Create new version history for an object named A
        A = self.klass.new('A')

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
        Test multiple {} comparison with forks
        """
        A = self.klass.new('A')
        a1 = A(self.replica)
        a2 = a1.nextv(self.replica)
        B = self.klass.new('B')
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
        Test that the {} string is compressed
        """
        A = self.klass.new('A')
        a = A(self.replica)
        B = self.klass.new('B')
        b = B(self.replica)

        self.assertEqual(str(a), "root->A.1")
        self.assertEqual(str(b), "root->B.1")

        for idx in xrange(100):
            a = a.nextv(self.replica)
            b = b.nextv(self.replica)

        self.assertEqual(str(a), "A.100->A.101")
        self.assertEqual(str(b), "B.100->B.101")


class LamportVersionTests(VersionSubclassCases, unittest.TestCase):

    klass = LamportVersion

    def test_lamport_scalar_compare(self):
        """
        Test comparisons of the lamport scalar data structure
        """
        # Assert Less
        self.assertLess(LamportScalar('r1', 10), LamportScalar('r1', 12))
        self.assertLess(LamportScalar('r1', 10), 12)
        self.assertLess(LamportScalar('r0', 10), LamportScalar('r1', 10))

        with self.assertRaises(TypeError):
            LamportScalar('r0', 10) < None

        # Assert Less Equal
        self.assertLessEqual(LamportScalar('r1', 10), LamportScalar('r1', 12))
        self.assertLessEqual(LamportScalar('r1', 10), 12)
        self.assertLessEqual(LamportScalar('r0', 10), LamportScalar('r1', 10))
        self.assertLessEqual(LamportScalar('r0', 10), LamportScalar('r0', 10))
        self.assertLessEqual(LamportScalar('r1', 12), LamportScalar('r1', 12))

        with self.assertRaises(TypeError):
            LamportScalar('r0', 10) <= None

        # Assert Equal/Not Equal
        self.assertEqual(LamportScalar('r1', 10), LamportScalar('r1', 10))
        self.assertEqual(LamportScalar('r1', 10), 10)
        self.assertNotEqual(LamportScalar('r1', 10), LamportScalar('r2', 10))
        self.assertNotEqual(LamportScalar('r1', 10), LamportScalar('r2', 18))
        self.assertNotEqual(LamportScalar('r1', 10), 18)
        self.assertNotEqual(LamportScalar('r10', 293), None)

        # Assert Greater
        self.assertGreater(LamportScalar('r1', 12), LamportScalar('r1', 10))
        self.assertGreater(12, LamportScalar('r1', 10))
        self.assertGreater(LamportScalar('r1', 10), LamportScalar('r0', 10))

        with self.assertRaises(TypeError):
            LamportScalar('r0', 10) > None

        # Assert Greater Equal
        self.assertGreaterEqual(LamportScalar('r1', 12), LamportScalar('r1', 10))
        self.assertGreaterEqual(12, LamportScalar('r1', 10))
        self.assertGreaterEqual(LamportScalar('r1', 10), LamportScalar('r0', 10))
        self.assertGreaterEqual(LamportScalar('r0', 10), LamportScalar('r0', 10))
        self.assertGreaterEqual(LamportScalar('r1', 12), LamportScalar('r1', 12))

        with self.assertRaises(TypeError):
            LamportScalar('r0', 10) >= None

    def test_lamport_increment(self):
        """
        Test the Lamport increment
        """
        alpha = self.replica
        bravo = random.choice([r for r in self.sim.replicas if r != alpha])

        # Set IDs for version comparison
        # NOTE that the string comparsion, "b0" > "a0" is True.
        alpha.id = "a0"
        bravo.id = "b0"

        Foo = self.klass.new('Foo')
        v1 = Foo(alpha)

        self.assertIsInstance(v1.version, LamportScalar)
        self.assertEqual(Foo.latest_version(), v1.version)
        self.assertEqual(v1.version, LamportScalar(alpha.id, 1))

        v2 = Foo(bravo)
        self.assertIsInstance(v2.version, LamportScalar)
        self.assertEqual(Foo.latest_version(), v2.version)
        self.assertEqual(v2.version, LamportScalar(bravo.id, 1))

        # Suprise, v2 is greater than v1!
        self.assertGreater(v2, v1)

        v3 = Foo(alpha)
        self.assertIsInstance(v3.version, LamportScalar)
        self.assertEqual(Foo.latest_version(), v3.version)
        self.assertEqual(v3.version, LamportScalar(alpha.id, 2))
        self.assertGreater(v3, v2)

    def test_lamport_update(self):
        """
        Test the Lamport update version method
        """
        alpha = self.replica
        bravo = random.choice([r for r in self.sim.replicas if r != alpha])

        # Set IDs for version comparison
        # NOTE that the string comparsion, "b0" > "a0" is True.
        alpha.id = "a0"
        bravo.id = "b0"

        # Create a sequence of alpha IDs
        Foo = self.klass.new('Foo')
        for _ in xrange(10):
            va = Foo(alpha)

        # Create a single bravo ID
        vb = Foo(bravo)

        # Assert that the va version is way greater.
        self.assertGreater(va, vb)

        # Now update vb with the latest va version
        Foo.update_version(bravo, va)

        vb = Foo(bravo)
        self.assertGreater(vb, va)

    def test_nextv(self):
        """
        Test getting the next {} of an object
        """
        alpha = self.replica
        bravo = random.choice([r for r in self.sim.replicas if r != alpha])

        # Set IDs for version comparison
        # NOTE that the string comparsion, "b0" > "a0" is True.
        alpha.id = "a0"
        bravo.id = "b0"

        v1 = self.klass(alpha)
        self.sim.env.now = 42
        v2 = v1.nextv(bravo)

        self.assertIsInstance(v2, self.klass)
        self.assertEqual(v2.parent, v1)
        self.assertEqual(v1.level, v2.level)

        self.assertFalse(v1.committed)
        self.assertFalse(v2.committed)

        self.assertGreater(v2.version, v1.version)
        self.assertGreater(v2.created, v1.created)
        self.assertGreater(v2.updated, v1.created)
        self.assertNotEqual(v2.writer, v1.writer)

        self.assertEqual(v1.counter, v2.counter)

    def test_replica_continuation(self):
        """
        Test the writing of multiple {}s on different replicas
        """
        alpha = self.replica
        bravo = random.choice([r for r in self.sim.replicas if r != alpha])

        # Set IDs for version comparison
        # NOTE that the string comparsion, "b0" > "a0" is True.
        alpha.id = "a0"
        bravo.id = "b0"

        Foo = self.klass.new('Foo')
        Bar = self.klass.new('Bar')

        f1 = Foo(alpha)
        self.sim.env.now += 10
        f2 = f1.nextv(bravo)

        self.sim.env.now += 10
        b1 = Bar(bravo)

        self.sim.env.now += 10
        b2 = b1.nextv(alpha)

        self.assertIsInstance(f2, Foo)
        self.assertIsInstance(b2, Bar)

        self.assertEqual(b2.parent, b1)
        self.assertEqual(f2.parent, f1)

        self.assertIsNot(b2.parent, f1)
        self.assertIsNot(f2.parent, b1)

        self.assertGreater(f2.version, f1.version)
        self.assertLess(b2.version, b1.version) # Surprise! Tie break by replica id!

        self.assertGreater(f2.created, f1.created)
        self.assertGreater(b1.created, f2.created)
        self.assertGreater(b2.created, b1.created)

    def test_version_string(self):
        """
        Test that the {} string is compressed
        """
        A = self.klass.new('A')
        a = A(self.replica)
        B = self.klass.new('B')
        b = B(self.replica)

        self.assertEqual(str(a), "root->A.{}.1".format(self.replica.id))
        self.assertEqual(str(b), "root->B.{}.1".format(self.replica.id))

        for idx in xrange(100):
            a = a.nextv(self.replica)
            b = b.nextv(self.replica)

        self.assertEqual(str(a), "A.{0}.100->A.{0}.101".format(self.replica.id))
        self.assertEqual(str(b), "B.{0}.100->B.{0}.101".format(self.replica.id))


class FederatedVersionTests(VersionSubclassCases, unittest.TestCase):

    klass = FederatedVersion

    def test_forte_version_compare(self):
        """
        Test comparisons of the federated forte versions
        """
        Foo = self.klass.new('Foo')
        v10 = Foo(self.replica)
        v10.version = 1
        v10.forte = 0

        v20 = Foo(self.replica)
        v20.version = 2
        v20.forte = 0

        v11 = Foo(self.replica)
        v11.version = 1
        v11.forte = 1

        v21 = Foo(self.replica)
        v21.version = 2
        v21.forte = 1

        # Assert Less
        self.assertLess(v10, v20)
        self.assertLess(v10, v11)
        self.assertLess(v10, v21)
        self.assertLess(v20, v11) # <-- This is an important one!
        self.assertLess(v11, v21)
        self.assertLess(v20, v21) # <-- This is another important one!
        self.assertLess(v10, 3)
        self.assertLess(v20, 3)
        self.assertLess(v11, 3)
        self.assertLess(v21, 3)

        with self.assertRaises(TypeError):
            v10 < None

        # Assert Less Equal
        self.assertLessEqual(v10, v10)
        self.assertLessEqual(v10, v20)
        self.assertLessEqual(v10, v11)
        self.assertLessEqual(v10, v21)
        self.assertLessEqual(v20, v20)
        self.assertLessEqual(v20, v11)
        self.assertLessEqual(v20, v21)
        self.assertLessEqual(v11, v11)
        self.assertLessEqual(v11, v21)
        self.assertLessEqual(v21, v21)
        self.assertLessEqual(v10, 1)
        self.assertLessEqual(v11, 1)
        self.assertLessEqual(v20, 2)
        self.assertLessEqual(v21, 2)
        self.assertLessEqual(v10, 2)
        self.assertLessEqual(v11, 2)
        self.assertLessEqual(v20, 3)
        self.assertLessEqual(v21, 3)

        with self.assertRaises(TypeError):
            v20 <= None

        # Assert Equal/Not Equal
        vnew = Foo(self.replica)
        vnew.version = 1
        vnew.forte = 0
        self.assertEqual(v10, vnew)
        self.assertEqual(v10, 1)
        self.assertNotEqual(v10, v20)
        self.assertNotEqual(v20, v11)
        self.assertNotEqual(v11, v21)
        self.assertNotEqual(v21, 1)
        self.assertNotEqual(v10, 0)
        self.assertNotEqual(v11, None)

        # Assert Greater
        self.assertGreater(v21, v11)
        self.assertGreater(v21, v20)
        self.assertGreater(v21, v20)
        self.assertGreater(v11, v20)
        self.assertGreater(v11, v10)
        self.assertGreater(v20, v10)
        self.assertGreater(3, v21)
        self.assertGreater(3, v11)
        self.assertGreater(3, v20)
        self.assertGreater(3, v10)

        with self.assertRaises(TypeError):
            v21 > None

        # Assert Greater Equal
        self.assertGreaterEqual(v21, v21)
        self.assertGreaterEqual(v21, v11)
        self.assertGreaterEqual(v21, v20)
        self.assertGreaterEqual(v21, v10)
        self.assertGreaterEqual(v11, v11)
        self.assertGreaterEqual(v11, v20)
        self.assertGreaterEqual(v11, v10)
        self.assertGreaterEqual(v20, v20)
        self.assertGreaterEqual(v20, v10)
        self.assertGreaterEqual(v10, v10)
        self.assertGreaterEqual(2, v21)
        self.assertGreaterEqual(1, v11)
        self.assertGreaterEqual(2, v20)
        self.assertGreaterEqual(1, v10)
        self.assertGreaterEqual(3, v21)
        self.assertGreaterEqual(3, v11)
        self.assertGreaterEqual(3, v20)
        self.assertGreaterEqual(3, v10)

        with self.assertRaises(TypeError):
            v11 >= None

    def test_parent_forte(self):
        """
        Test that the parent's forte is kept.
        """

        A = self.klass.new('A')
        a1 = A(self.replica)

        self.assertEqual(a1.forte, 0)

        a2 = a1.nextv(self.replica)
        self.assertEqual(a1.forte, 0)
        self.assertEqual(a1.forte, a2.forte)

        a1.forte = 1

        a3 = a1.nextv(self.replica)
        self.assertEqual(a1.forte, 1)
        self.assertEqual(a1.forte, a3.forte)
        self.assertNotEqual(a2.forte, a3.forte)

        a4 = a2.nextv(self.replica)
        self.assertEqual(a1.forte, 1)
        self.assertEqual(a1.forte, a3.forte)
        self.assertNotEqual(a2.forte, a3.forte)
        self.assertEqual(a2.forte, 0)
        self.assertEqual(a2.forte, a4.forte)

    def test_update_forte(self):
        """
        Test that a Raft leader can update the forte.
        """
        # Make replica a strong leader
        alpha  = self.replica
        leader = random.choice([r for r in self.sim.replicas if r != alpha])
        leader.consistency = Consistency.STRONG
        leader.state = State.LEADER

        A = self.klass.new('A')
        a = A(alpha)

        for _ in xrange(5):
            a = a.nextv(alpha)
            self.assertEqual(a.forte, 0)

        a.update(leader, commit=True, forte=True)
        self.assertEqual(a.forte, 1)

        for _ in xrange(5):
            a = a.nextv(alpha)
            self.assertEqual(a.forte, 1)

        a.update(leader, commit=True, forte=True)
        self.assertEqual(a.forte, 2)

    def test_non_leader_forte_update(self):
        """
        Assert that only Raft leaders can update the Forte
        """
        # Make replica a strong leader
        alpha  = self.replica
        leader = random.choice([r for r in self.sim.replicas if r != alpha])

        P = self.klass.new('P')
        p = P(alpha)

        with self.assertRaises(SimulationException):
            p.update(leader, commit=True, forte=True)

        leader.consistency = Consistency.STRONG

        with self.assertRaises(SimulationException):
            p.update(leader, commit=True, forte=True)

        leader.state = State.LEADER
        p.update(leader, commit=True, forte=True)

        self.assertEqual(p.forte, 1)

    def test_version_string(self):
        """
        Test that the {} string is compressed
        """
        A = self.klass.new('A')
        a = A(self.replica)
        B = self.klass.new('B')
        b = B(self.replica)

        self.assertEqual(str(a), "root->A.1.0")
        self.assertEqual(str(b), "root->B.1.0")

        for idx in xrange(100):
            a = a.nextv(self.replica)
            b = b.nextv(self.replica)

        self.assertEqual(str(a), "A.100.0->A.101.0")
        self.assertEqual(str(b), "B.100.0->B.101.0")

        a.forte = A.increment_forte()
        b.forte = B.increment_forte()

        self.assertEqual(str(a), "A.100.0->A.101.1")
        self.assertEqual(str(b), "B.100.0->B.101.1")

        for idx in xrange(7):
            a = a.nextv(self.replica)
            b = b.nextv(self.replica)

        self.assertEqual(str(a), "A.107.1->A.108.1")
        self.assertEqual(str(b), "B.107.1->B.108.1")
