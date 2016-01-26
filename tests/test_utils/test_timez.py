# tests.test_utils.test_timez
# Testing for the time and timezone utilities.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 11:14:48 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_timez.py [] benjamin@bengfort.com $

"""
Testing for the time and timezone utilities.
"""

##########################################################################
## Imports
##########################################################################

import unittest
import datetime

from cloudscope.utils.timez import humanizedelta


##########################################################################
## Helper Functions Test Cases
##########################################################################

class TimezHelpersTests(unittest.TestCase):

    def test_humanizedelta(self):
        """
        Test the humanize delta function to convert seconds
        """
        cases = (
            (12512334, "144 days 19 hours 38 minutes 54 seconds"),
            (34321, "9 hours 32 minutes 1 second"),
            (3428, "57 minutes 8 seconds"),
            (1, "1 second"),
            (0.21, "0 second"),
        )

        for seconds, expected in cases:
            self.assertEqual(humanizedelta(seconds=seconds), expected)

    def test_humanizedelta_milliseconds(self):
        """
        Test the humanize delta function to conver milliseconds
        """

        # Case with seconds already there
        self.assertEqual(humanizedelta(seconds=10, milliseconds=2000), '12 seconds')

        # Case without seconds present
        self.assertEqual(humanizedelta(milliseconds=456875), '7 minutes 36 seconds')
