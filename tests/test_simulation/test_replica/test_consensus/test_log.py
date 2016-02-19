# tests.test_simulation.test_replica.test_consensus.test_log
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

import unittest

from cloudscope.simulation.replica.consensus.log import WriteLog

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
