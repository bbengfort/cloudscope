# test.test_utils.test_decorators
# Testing the decorators utility package.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Feb 23 10:33:50 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_decorators.py [8d16e6c] benjamin@bengfort.com $

"""
Testing the decorators utility package.
"""

##########################################################################
## Imports
##########################################################################

import time
import unittest

from cloudscope.utils.decorators import *

try:
    from unittest import mock
except ImportError:
    import mock


##########################################################################
## Decorators Tests
##########################################################################

class DecoratorsTests(unittest.TestCase):
    """
    Basic decorators utility tests.
    """

    def test_memoized(self):
        """
        Test the memoized property
        """

        class Thing(object):

            @memoized
            def attr(self):
                return 42

        thing = Thing()
        self.assertFalse(hasattr(thing, '_attr'))
        self.assertEqual(thing.attr, 42)
        self.assertTrue(hasattr(thing, '_attr'))

    def test_timer(self):
        """
        Test the Timer context manager
        """
        with Timer() as t:
            time.sleep(1)

        self.assertGreater(t.finished, t.started)
        self.assertEqual(t.elapsed, t.finished-t.started)
        self.assertEqual(str(t), '1 seconds')

        data = t.serialize()
        for key in ('started', 'finished', 'elapsed'):
            self.assertIn(key, data)

    def test_timeit(self):
        """
        Test the timeit decorator
        """

        @timeit
        def myfunc():
            return 42

        output = myfunc()
        self.assertEqual(len(output), 2)
        result, timer = output
        self.assertEqual(result, 42)
        self.assertTrue(isinstance(timer, Timer))
