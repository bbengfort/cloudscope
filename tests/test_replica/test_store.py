# tests.test_store
# Tests the store functionality in the simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 12:40:47 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_store.py [] benjamin@bengfort.com $

"""
Tests the store functionality in the simulation.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.dynamo import Sequence
from cloudscope.replica import Replica, Version

try:
    from unittest import mock
except ImportError:
    import mock

##########################################################################
## Version Tests
##########################################################################

class VersionTests(unittest.TestCase):

    def test_version_string(self):
        """
        Test that the version string is compressed.
        """
        simulation = mock.MagicMock()
        simulation.env.now = 23

        # Reset the version counter
        Version.counter = Sequence()

        replica = Replica(simulation)
        version = Version(replica)

        self.assertEqual(str(version), "root->1")

        for idx in xrange(100):
            version = version.fork(replica)

        self.assertEqual(str(version), "100->101")

    @unittest.skip("Not implemented correctly yet.")
    def test_forked_version_string(self):
        """
        Test the compressability of a forked version string.
        """
        simulation = mock.MagicMock()
        simulation.env.now = 23

        # Reset the version counter
        # TODO: move to a setup function
        Version.counter = Sequence()

        replica = Replica(simulation)
        version = Version(replica)

        for idx in xrange(5):
            version = version.fork(replica)

        # Now we split
        version_a = version.fork(replica)
        version_b = version.fork(replica)

        for idx in xrange(3):
            version_a = version_a.fork(replica)

        for idx in xrange(9):
            version_b = version_b.fork(replica)

        self.assertEqual(str(version_a), '')
        self.assertEqual(str(version_b), '')
