# tests.test_utils.test_serialize
# Test the serialize utility module.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Feb 23 10:42:26 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_serialize.py [8d16e6c] benjamin@bengfort.com $

"""
Test the serialize utility module.
"""

##########################################################################
## Imports
##########################################################################

import json
import unittest
import datetime
import numpy as np

from cloudscope.utils.serialize import *

try:
    from unittest import mock
except ImportError:
    import mock

##########################################################################
## Fixture
##########################################################################

class Thing(object):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def serialize(self):
        return self.kwargs

##########################################################################
## Serialize Tests
##########################################################################

class SerializeTests(unittest.TestCase):
    """
    Basic serialization utility tests.
    """

    def test_serialize_complex(self):
        """
        Test the serialization of a complex object
        """
        def generator():
            for x in xrange(1,4):
                yield x

        thing = Thing(
            time = datetime.datetime(2015, 12, 12, 13, 42, 21, 0),
            data = np.array([1,2,3]),
            gens = generator(),
            nest = Thing(name='bob', color='red'),
        )

        expected = {
            'time': '2015-12-12T13:42:21.000000Z',
            'data': [1,2,3],
            'gens': [1,2,3],
            'nest': {
                'name': 'bob', 'color': 'red',
            }
        }

        self.assertEqual(json.dumps(expected), json.dumps(thing, cls=JSONEncoder))
