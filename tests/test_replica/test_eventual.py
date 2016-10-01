# tests.test_replica.test_eventual
# Testing for the methods and properties of eventual replicas.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Sep 30 20:40:43 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_eventual.py [] benjamin@bengfort.com $

"""
Testing for the methods and properties of eventual replicas.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.replica import Replica
from cloudscope.replica.eventual import *
from cloudscope.simulation.main import ConsistencySimulation
from cloudscope.replica.store.vcs import Version, FederatedVersion
from cloudscope.config import settings

try:
    from unittest import mock
except ImportError:
    import mock


##########################################################################
## Eventually Consistent Replica Tests
##########################################################################

class EventualReplicaTests(unittest.TestCase):

    # TODO: Implement these tests!

    def setUp(self):
        self.sim = ConsistencySimulation()
        Replica.counter.reset()

    def tearDown(self):
        self.sim = None


##########################################################################
## Backpressure Tests
##########################################################################

class BackpressureTests(unittest.TestCase):
    """
    These tests implement the various backpressure cases.
    """

    def setUp(self):
        self.sim = ConsistencySimulation()
        Replica.counter.reset()

        self.alpha = EventualReplica(self.sim)
        self.bravo = EventualReplica(self.sim)
        self.delta = EventualReplica(self.sim)

        self.sim.replicas = [
            self.alpha, self.bravo, self.delta
        ]

        self.versions = []
        self.orig_versioning = settings.simulation.versioning
        settings.simulation.versioning = 'federated'

    def tearDown(self):
        self.alpha = None
        self.bravo = None
        self.delta = None
        self.sim = None
        self.versions = []
        settings.simulation.versioning = self.orig_versioning

    def build_logs(self):
        """
        This builds the default log scenario for most test cases
        """

        # Create the foo object
        Foo = FederatedVersion.new('Foo')

        # Add our version tree with a fork, even version on one side, odd
        # version numbers on the other side. Alpha writes the first and even
        # version numbers while Bravo writes the odd versions greater than 3.
        self.versions.append(Foo(self.alpha))                      # Foo.1.0
        self.versions.append(self.versions[0].nextv(self.alpha))   # Foo.2.0
        self.versions.append(self.versions[0].nextv(self.bravo))   # Foo.3.0 (fork)
        self.versions.append(self.versions[1].nextv(self.alpha))   # Foo.4.0
        self.versions.append(self.versions[2].nextv(self.bravo))   # Foo.5.0 (fork)
        self.versions.append(self.versions[3].nextv(self.alpha))   # Foo.6.0
        self.versions.append(self.versions[4].nextv(self.bravo))   # Foo.7.0 (fork)
        self.versions.append(self.versions[5].nextv(self.alpha))   # Foo.8.0
        self.versions.append(self.versions[6].nextv(self.bravo))   # Foo.9.0 (fork)

        # Add the first and even versions to alpha
        for vers in self.versions:
            if vers.version == 1 or vers.version % 2 == 0:
                self.alpha.log.append(vers, 0)

        # Add the first and odd versions to bravo
        for vers in self.versions:
            if vers.version == 1 or vers.version % 2 == 1:
                self.bravo.log.append(vers, 0)

        # Add all versions to delta except Foo.6.0 and Foo.8.0
        for vers in self.versions:
            if vers.version < 6 or vers.version % 2 == 1:
                self.delta.log.append(vers, 0)

    def test_federated_versions_only(self):
        """
        Assert that only in federated versioning does anything happen.
        """
        settings.simulation.versioning = 'default'
        self.build_logs()

        # In federated versioning, this would change bravo's log.
        current  = self.bravo.log.get_latest_version('Foo')
        orig_log = self.bravo.log.freeze()
        v2 = self.versions[1]
        v2.forte = 1

        replaced = self.bravo.update_forte_children(current, v2)
        self.assertEqual(replaced, current)
        self.assertEqual(self.bravo.log.freeze(), orig_log)

    def test_no_harm_remote_lte(self):
        """
        Assert no change in the log when the current >= remote
        """
        self.build_logs()
        current  = self.delta.log.get_latest_version('Foo')
        remote   = self.versions[-1]
        orig_log = self.delta.log.freeze()

        # When current == remote
        self.assertEqual(current, self.delta.update_forte_children(current, remote))
        self.assertEqual(self.delta.log.freeze(), orig_log)

        # When current > remote
        remote = self.versions[-2]
        self.assertEqual(current, self.delta.update_forte_children(current, remote))
        self.assertEqual(self.delta.log.freeze(), orig_log)

    def test_backpressure_only_on_log(self):
        """
        Ensure that backpressure only affects versions in the log
        """
        Bar = FederatedVersion.new('Bar')
        v1 = Bar(self.alpha)
        v2 = v1.nextv(self.alpha)
        self.alpha.log.append(v1, 0)
        self.alpha.log.append(v2, 0)

        others = []
        v = v2
        for _ in xrange(5):
            v = v.nextv(self.alpha)
            others.append(v)

        v3 = v.nextv(self.alpha)
        self.alpha.log.append(v3, 0)
        v4 = v3.nextv(self.alpha)
        self.alpha.log.append(v4, 0)

        self.assertEqual(v4.version, 9)
        v1.forte = 1
        self.assertEqual(self.alpha.log.get_latest_version('Bar'), v4)
        current = self.alpha.update_forte_children(v4, v1)
        self.assertEqual(current, v4)

        for v in (v1, v2, v3, v4):
            self.assertEqual(v.forte, 1)

        for v in others:
            self.assertEqual(v.forte, 0)

    def test_backpressure_log_rearrange(self):
        """
        Test how backpressure rearranges the log
        """

        def assertLogOrder(log, order):
            self.assertEqual(len(log)-1, len(order))
            for idx, vers in enumerate(order):
                self.assertEqual(log[idx+1].version, vers)

        Baz = FederatedVersion.new('Baz')

        v1 = Baz(self.alpha)
        v2 = v1.nextv(self.alpha)
        v3 = v1.nextv(self.bravo) # Fork!
        v4 = v2.nextv(self.alpha)
        v5 = v3.nextv(self.bravo)
        v6 = v4.nextv(self.alpha)
        v7 = v5.nextv(self.bravo)

        # Baz.1.0 -> Baz.2.0 -> Baz.4.0 -> Baz.6.0
        # Baz.1.0 -> Baz.3.0 -> Baz.5.0 -> Baz.7.0

        for v in (v1,v2,v3,v4,v5,v7):
            self.delta.log.append(v, 0)

        # Move v4, the end of the v2 fork in this log to the end.
        v2.forte = 1
        self.delta.update_forte_children(self.delta.log.get_latest_version('Baz'), v2)
        assertLogOrder(self.delta.log, (v1,v2,v3,v5,v7,v4))

        self.delta.log.truncate()
        for v in (v1,v2,v3,v4,v5,v6,v7): v.forte = 0

        for v in (v1,v3,v7,v2,v4,v6):
            self.delta.log.append(v, 0)

        # Move v7, the out of order fork in this log to the end.
        v3.forte = 1
        self.delta.update_forte_children(self.delta.log.get_latest_version('Baz'), v3)
        assertLogOrder(self.delta.log, (v1,v3,v2,v4,v6,v7))

    def test_backpressure_case_one(self):
        """
        Test backpressure case one: Foo.1.0 -> Foo.1.1

        This will be applied to all replicas, it is expected that all versions
        become marked with the new forte number, but the ordering doesn't
        change and that the current returned remains identical.
        """
        self.build_logs()
        remote  = self.versions[0]
        self.assertEqual(remote.version, 1)
        self.assertEqual(remote.forte, 0)

        remote.forte = 1 # Update the forte number!

        for replica in (self.alpha, self.bravo, self.delta):
            current  = replica.log.get_latest_version('Foo')
            orig_log = replica.log.freeze()
            returned = replica.update_forte_children(current, remote)

            self.assertEqual(orig_log, replica.log.freeze()) # The log entries will be modified, but they'll be the same
            self.assertEqual(current, returned) # The forte numbers will be modified, but they'll be the same

            # All the forte numbers are updated
            for entry in replica.log[1:]:
                self.assertEqual(entry.version.forte, 1)

    def test_backpressure_case_two_alpha(self):
        """
        Test backpressure case two alpha: Foo.2.0 -> Foo.2.1
        Expected: Alpha will have all versions marked, current unchanged
        """
        self.build_logs()
        remote = self.versions[1]

        self.assertEqual(remote.version, 2)
        self.assertEqual(remote.forte, 0)

        remote.forte = 1 # Update the forte number!

        # Test Alpha case
        current  = self.alpha.log.get_latest_version('Foo')
        orig_log = self.alpha.log.freeze()
        returned = self.alpha.update_forte_children(current, remote)
        self.assertEqual(current, returned)
        self.assertEqual(orig_log, self.alpha.log.freeze())

        for entry in self.alpha.log[1:]:
            if entry.version.version > 1:
                self.assertEqual(entry.version.forte, 1)
            else:
                self.assertEqual(entry.version.forte, 0)

    def test_backpressure_case_two_bravo(self):
        """
        Test backpressure case two bravo: Foo.2.0 -> Foo.2.1
        Expected: Bravo will have no versions marked, current unchanged
        """
        self.build_logs()
        remote = self.versions[1]

        self.assertEqual(remote.version, 2)
        self.assertEqual(remote.forte, 0)

        remote.forte = 1 # Update the forte number!

        # Test Bravo case
        current  = self.bravo.log.get_latest_version('Foo')
        orig_log = self.bravo.log.freeze()
        returned = self.bravo.update_forte_children(current, remote)
        self.assertEqual(current, returned)
        self.assertEqual(orig_log, self.bravo.log.freeze())

        for entry in self.bravo.log[1:]:
            self.assertEqual(entry.version.forte, 0)

    def test_backpressure_case_two_delta(self):
        """
        Test backpressure case two delta: Foo.2.0 -> Foo.2.1
        Expected: Delta will have even versions marked and current = Foo.4.1
        """
        self.build_logs()
        remote = self.versions[1]

        self.assertEqual(remote.version, 2)
        self.assertEqual(remote.forte, 0)

        remote.forte = 1 # Update the forte number!

        # Test Delta case
        current  = self.delta.log.get_latest_version('Foo')
        orig_log = self.delta.log.freeze()
        returned = self.delta.update_forte_children(current, remote)
        self.assertNotEqual(current, returned)
        self.assertEqual(self.versions[3], returned)
        self.assertNotEqual(orig_log, self.delta.log.freeze())

        # Test the new ordering
        new_log = list(orig_log)
        new_log.append(new_log[4]._replace(term=1))
        del new_log[4]

        self.assertEqual(self.delta.log.freeze(), tuple(new_log))

        for entry in self.delta.log[1:]:
            if entry.version.version % 2 == 0:
                self.assertEqual(entry.version.forte, 1)
            else:
                self.assertEqual(entry.version.forte, 0)

    def test_backpressure_case_three_alpha(self):
        """
        Test backpressure case three alpha: Foo.3.0 -> Foo.3.1
        Expected: Alpha will have no versions marked, current unchanged
        """
        self.build_logs()
        remote = self.versions[2]

        self.assertEqual(remote.version, 3)
        self.assertEqual(remote.forte, 0)

        remote.forte = 1 # Update the forte number!

        # Test Alpha case
        current  = self.alpha.log.get_latest_version('Foo')
        orig_log = self.alpha.log.freeze()
        returned = self.alpha.update_forte_children(current, remote)
        self.assertEqual(current, returned)
        self.assertEqual(orig_log, self.alpha.log.freeze())

        for entry in self.alpha.log[1:]:
            self.assertEqual(entry.version.forte, 0)

    def test_backpressure_case_three_bravo(self):
        """
        Test backpressure case two bravo: Foo.3.0 -> Foo.3.1
        Expected: Bravo will have all versions marked, current unchanged
        """
        self.build_logs()
        remote = self.versions[2]

        self.assertEqual(remote.version, 3)
        self.assertEqual(remote.forte, 0)

        remote.forte = 1 # Update the forte number!

        # Test Bravo case
        current  = self.bravo.log.get_latest_version('Foo')
        orig_log = self.bravo.log.freeze()
        returned = self.bravo.update_forte_children(current, remote)
        self.assertEqual(current, returned)
        self.assertEqual(orig_log, self.bravo.log.freeze())

        for entry in self.bravo.log[1:]:
            if entry.version.version > 1:
                self.assertEqual(entry.version.forte, 1)
            else:
                self.assertEqual(entry.version.forte, 0)

    def test_backpressure_case_three_delta(self):
        """
        Test backpressure case three delta: Foo.3.0 -> Foo.3.1
        Expected: Delta will have odd versions marked (but 1) and current unchanged
        """
        self.build_logs()
        remote = self.versions[2]

        self.assertEqual(remote.version, 3)
        self.assertEqual(remote.forte, 0)

        remote.forte = 1 # Update the forte number!

        # Test Delta case
        current  = self.delta.log.get_latest_version('Foo')
        orig_log = self.delta.log.freeze()
        returned = self.delta.update_forte_children(current, remote)
        self.assertEqual(current, returned)
        self.assertEqual(current, returned)
        self.assertEqual(orig_log, self.delta.log.freeze())

        for entry in self.delta.log[1:]:
            if entry.version.version > 1 and entry.version.version % 2 == 1:
                self.assertEqual(entry.version.forte, 1)
            else:
                self.assertEqual(entry.version.forte, 0)
