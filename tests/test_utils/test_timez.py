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

from datetime import datetime
from dateutil import parser
from dateutil.tz import tzlocal, tzutc
from cloudscope.utils.timez import *


##########################################################################
## Helper Functions Test Cases
##########################################################################

class TimezHelpersTests(unittest.TestCase):

    def setUp(self):
        self.localnow = datetime.now(tzlocal()).replace(microsecond=0)
        self.utcnow   = self.localnow.astimezone(tzutc())

    def tearDown(self):
        self.localnow = self.utcnow = None

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

    def test_strptimez(self):
        """
        Test the parsing of timezone aware date strings
        """
        dtfmt = "%Y-%m-%dT%H:%M:%S%z"

        cases = (
            ('2012-12-27T12:53:12-0500', datetime(2012, 12, 27, 17, 53, 12, tzinfo=tzutc())),
            ('2012-12-27T12:53:12+0800', datetime(2012, 12, 27, 4, 53, 12, tzinfo=tzutc())),
        )

        for dtstr, dt in cases:
            self.assertEqual(dt, strptimez(dtstr, dtfmt))

        # Non-timezone case
        self.assertEqual(
            strptimez('2012-12-27T12:53:12', "%Y-%m-%dT%H:%M:%S"),
            datetime(2012, 12, 27, 12, 53, 12)
        )

    def test_strptimez_no_z(self):
        """
        Assert that strptimez works with no '%z'
        This should return a timezone naive datetime
        """
        dtfmt = "%a %b %d %H:%M:%S %Y"
        dtstr = self.localnow.strftime(dtfmt)
        self.assertEqual(strptimez(dtstr, dtfmt), self.localnow.replace(tzinfo=None))


    def test_strptimez_no_space(self):
        """
        Non-space delimited '%z' works
        """
        dtfmt = "%Y-%m-%dT%H:%M:%S%z"
        dtstr = self.localnow.strftime(dtfmt)
        self.assertEqual(strptimez(dtstr, dtfmt), self.utcnow)

    def test_begin_z(self):
        """
        Test fmt that begins with '%z'
        """
        dtfmt = "%z %H:%M:%S for %Y-%m-%d"
        dtstr = self.localnow.strftime(dtfmt)
        self.assertEqual(strptimez(dtstr, dtfmt), self.utcnow)

    def test_middle_z(self):
        """
        Test fmt that contains '%z'
        """
        dtfmt = "time is: %H:%M:%S %z on %Y-%m-%d "
        dtstr = self.localnow.strftime(dtfmt)
        self.assertEqual(strptimez(dtstr, dtfmt), self.utcnow)


class EpochTests(unittest.TestCase):

    CASES = (
        (1431991818,     "Mon, 18 May 2015 19:30:18 -0400"),
        (1431999232.0,   "Mon, 18 May 2015 18:33:52 -0700"),
        ("1431999621.0", "Tue, 19 May 2015 01:40:21 +0000 (UTC)"),
        (1434039260,     "Thu, 11 Jun 2015 16:14:20 +0000 (UTC)"),
        (1434039507.0,   "Thu, 11 Jun 2015 12:18:27 -0400"),
        ("1434040991",   "Thu, 11 Jun 2015 09:43:11 -0700"),
        (1432379758,     "Sat, 23 May 2015 04:15:58 -0700 (PDT)"),
        (1433270932.0,   "Tue, 02 Jun 2015 18:48:52 +0000"),
        ("1433278213",   "Tue, 2 Jun 2015 16:50:13 -0400"),
    )


    def test_epochftime(self):
        """
        Test the ability to turn a datetime into an epoch
        """
        for epoch, case in self.CASES:
            case  = parser.parse(case)
            epoch = int(float(epoch))
            self.assertEqual(epochftime(case), epoch)

    def test_epochptime(self):
        """
        Test the ability to turn an epoch into a datetime
        """
        for epoch, case in self.CASES:
            case  = parser.parse(case)
            epoch = int(float(epoch))
            self.assertEqual(case, epochptime(epoch))
