# tests.test_simulation.test_replica.test_strore.test_log
# Testing the data structures and helpers for a Raft write log.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Feb 19 11:05:18 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_log.py [] benjamin@bengfort.com $

"""
Testing the data structures and helpers for a Raft write log.
"""

##########################################################################
## Imports
##########################################################################

import random
import unittest

from cloudscope.replica.store import Version
from cloudscope.replica.store import WriteLog
from cloudscope.replica.store import MultiObjectWriteLog

from tests.test_replica import get_mock_simulation

##########################################################################
## TestCase
##########################################################################

class WriteLogTests(unittest.TestCase):

    def test_log_append(self):
        """
        Test creating and appending to a write log
        """
        log = WriteLog()
        self.assertEqual(log.lastApplied, 0)
        self.assertEqual(log.lastVersion, None)
        self.assertEqual(log.lastTerm, 0)

        version = 0
        for term in xrange(1, 5):
            for x in xrange(1, 10):
                version += 1
                log.append(version, term)

        self.assertEqual(log.lastApplied, len(log) - 1)
        self.assertEqual(log.lastVersion, version)
        self.assertEqual(log.lastTerm, 4)

    def test_log_remove(self):
        """
        Test remove from a log
        """
        log = WriteLog()

        version = 0
        for term in xrange(1, 5):
            for x in xrange(1, 10):
                version += 1
                log.append(version, term)

        self.assertEqual(log.lastApplied, len(log) - 1)
        self.assertEqual(log.lastVersion, version)
        self.assertEqual(log.lastTerm, 4)

        log.remove(30)

        self.assertEqual(len(log), 30)
        self.assertEqual(log.lastApplied, len(log) - 1)
        self.assertEqual(log.lastVersion, version-7)
        self.assertEqual(log.lastTerm, 4)

    def test_log_empty(self):
        """
        Test completely empty a log
        """
        log = WriteLog()

        version = 0
        for term in xrange(1, 5):
            for x in xrange(1, 10):
                version += 1
                log.append(version, term)

        self.assertEqual(log.lastApplied, len(log) - 1)
        self.assertEqual(log.lastVersion, version)
        self.assertEqual(log.lastTerm, 4)

        log.remove()

        self.assertEqual(log.lastApplied, 0)
        self.assertEqual(log.lastVersion, None)
        self.assertEqual(log.lastTerm, 0)

    def test_log_more_up_to_date(self):
        """
        Test figuring out which log is more up to date
        """

        outofdate = WriteLog()
        uptodate  = WriteLog()

        # Add some log records
        version = 0
        for term in xrange(1, 5):
            for x in xrange(1, 10):
                version += 1
                outofdate.append(version, term)
                uptodate.append(version, term)

        # Make sure they're greater/less equal to start
        self.assertEqual(uptodate, outofdate)
        self.assertGreaterEqual(uptodate, outofdate)
        self.assertLessEqual(outofdate, uptodate)

        # Make out of date more and more out of date.
        # To ensure both different terms and different lengths.
        while outofdate.lastApplied > 0:
            outofdate.remove(outofdate.lastApplied)
            self.assertNotEqual(uptodate, outofdate)
            self.assertGreater(uptodate, outofdate)
            self.assertLess(outofdate, uptodate)


class MultiObjectWriteLogTests(unittest.TestCase):

    def setUp(self):
        # Replica fixture
        simulation = get_mock_simulation()
        replica = lambda: random.choice(simulation.replicas)

        # Version fixtures
        a = Version.new('A')(replica())
        b = Version.new('B')(replica())
        c = Version.new('C')(replica())
        d = Version.new('D')(replica())

        # Create mock log
        self.log = MultiObjectWriteLog()
        for obj in (a, b, c):
            self.log.append(obj, 1)

        # Create unordered log objects.
        self.log.append(a.fork(replica()), 2)
        self.log.append(a.fork(replica()), 2)
        self.log.append(a.fork(replica()), 2)
        self.log.append(a.fork(replica()), 3)
        self.log.append(a.fork(replica()), 3)
        self.log.append(b.fork(replica()), 3)
        self.log.append(b.fork(replica()), 4)
        self.log.append(b.fork(replica()), 4)
        self.log.append(c.fork(replica()), 4)
        self.log.append(d, 5)

        self.log.commitIndex = 9

    def tearDown(self):
        self.log = None

    def test_log_fixture(self):
        """
        Test the multi-object log fixture for completeness.
        """
        self.assertEqual(len(self.log), 14)
        self.assertEqual(self.log.commitIndex, 9)
        self.assertEqual(self.log.lastApplied, 13)

    def test_search_functionality(self):
        """
        Test the multi-object log search mechanism
        """

        (a, t) = self.log.search('A')
        self.assertEqual(a.version, 6)

        (c, t) = self.log.search('C')
        self.assertEqual(c.version, 2)

        (c, t) = self.log.search('C', 5)
        self.assertEqual(c.version, 1)

    def test_latest_version(self):
        """
        Test the multi-object log latest version function
        """

        a = self.log.get_latest_version('A')
        self.assertEqual(a.version, 6)

        b = self.log.get_latest_version('B')
        self.assertEqual(b.version, 4)

        c = self.log.get_latest_version('C')
        self.assertEqual(c.version, 2)

        d = self.log.get_latest_version('D')
        self.assertEqual(d.version, 1)

    def test_latest_commit(self):
        """
        Test the multi-object log latest version function
        """

        a = self.log.get_latest_commit('A')
        self.assertEqual(a.version, 6)

        b = self.log.get_latest_commit('B')
        self.assertEqual(b.version, 2)

        c = self.log.get_latest_commit('C')
        self.assertEqual(c.version, 1)

        d = self.log.get_latest_commit('D')
        self.assertIsNone(d)
