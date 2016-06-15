# tests
# Testing for the cloudscope package
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sat Jan 09 09:54:18 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [26b95c0] benjamin@bengfort.com $

"""
Testing for the cloudscope package
"""

##########################################################################
## Imports
##########################################################################

import unittest

##########################################################################
## Module Constants
##########################################################################

TEST_VERSION = "0.4" ## Also the expected version of the package

##########################################################################
## Test Cases
##########################################################################

class InitializationTest(unittest.TestCase):

    def test_initialization(self):
        """
        Tests a simple world fact by asserting that 10**2 is 100.
        """
        self.assertEqual(2+4, 6)

    def test_import(self):
        """
        Can import cloudscope
        """
        try:
            import cloudscope
        except ImportError:
            self.fail("Unable to import the cloudscope module!")

    def test_version(self):
        """
        Assert that the version is sane
        """
        import cloudscope
        self.assertEqual(TEST_VERSION, cloudscope.__version__)
