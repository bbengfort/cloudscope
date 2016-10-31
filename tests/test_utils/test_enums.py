# tests.test_utils.test_enums
# Test the helper enumeration object that we're using in Cloudscope.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Apr 01 15:14:55 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_enums.py [448d930] benjamin@bengfort.com $

"""
Test the helper enumeration object that we're using in Cloudscope.
"""

##########################################################################
## Imports
##########################################################################

import json
import unittest

from cloudscope.utils.enums import *
from cloudscope.utils.serialize import JSONEncoder

try:
    from unittest import mock
except ImportError:
    import mock


##########################################################################
## Logger Tests
##########################################################################

class EnumTests(unittest.TestCase):
    """
    Basic extended Enum tests.
    """

    def test_get(self):
        """
        Test case insensitive lookups via the get.
        """
        keys    = 'Mon Tue Wed Thu Fri Sat Sun'.split()

        DayU    = Enum('DayU', 'MON TUE WED THU FRI SAT SUN')
        DayL    = Enum('DayL', 'mon tue wed thu fri sat sun')
        DayC    = Enum('DayC', 'Mon Tue Wed Thu Fri Sat Sun')

        cases   = ((DayU, 'upper'), (DayL, 'lower'), (DayC, 'title'))
        actions = {
            'upper': lambda s: s.upper(),
            'lower': lambda s: s.lower(),
            'title': lambda s: s.title(),
        }

        # Assert that there are key errors without using get
        for key in keys:
            for enum, case in cases:
                for method, action in actions.items():
                    if method != case:
                        with self.assertRaises(KeyError):
                            enum[action(key)]

        # Assert that there are no key errors when using get
        for key in keys:
            for enum, case in cases:
                for method, action in actions.items():
                    print enum.get(action(key))
                    self.assertEqual(enum.get(action(key)), enum[actions[case](key)])

    def test_get_with_instance(self):
        """
        Test passing an enum member to the get method.
        """
        Day = Enum('Day', 'Mon Tue Wed Thu Fri Sat Sun')
        for member in Day:
            self.assertEqual(Day.get(member), member)

    @unittest.skip("Not sure why this doesn't work, straight from Python docs")
    def test_aliases(self):
        """
        Test aliases method on the enum.
        """

        class Day(Enum):
            Mon = 1
            Tue = 2
            Wed = 3
            Thu = 4
            Fri = 5
            Sat = 6
            Sun = 7

            Monday    = 1
            Tuesday   = 2
            Wednesday = 3
            Thursday  = 4
            Friday    = 5
            Saturday  = 6
            Sunday    = 7

        self.assertEqual([d.name for d in Day.aliases()], [
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
        ])

    def test_describe(self):
        """
        Test the describe method for enumerations.
        """

        Day = Enum('Day', 'Mon Tue Wed Thu Fri Sat Sun')
        cases = (
            ('Mon', 1),
            ('Tue', 2),
            ('Wed', 3),
            ('Thu', 4),
            ('Fri', 5),
            ('Sat', 6),
            ('Sun', 7),
        )

        for day, case in zip(Day, cases):
            self.assertEqual(day.describe(), case)

    def test_serialization(self):
        """
        Assert that a list of days can be serialized using JSON
        """

        Day = Enum('Day', 'Mon Tue Wed Thu Fri Sat Sun')
        classes = [Day.Mon, Day.Wed]
        event   = {
            "rehersal": Day.Fri,
            "wedding": Day.Sat,
            "presents": Day.Sun,
        }

        self.assertEqual(json.dumps(classes, cls=JSONEncoder), json.dumps(["mon", "wed"]))
        self.assertEqual(json.dumps(event, cls=JSONEncoder), json.dumps({
            "rehersal": "fri",
            "wedding": "sat",
            "presents": "sun",
        }))
