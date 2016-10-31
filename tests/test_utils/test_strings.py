# tests.test_utils.test_strings
# Testing the string helper functions.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Apr 05 07:35:00 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_strings.py [f37a55a] benjamin@bengfort.com $

"""
Testing the string helper functions.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.utils.strings import *

##########################################################################
## Test Case
##########################################################################

class StringsTests(unittest.TestCase):

    def test_camelize(self):
        """
        Test the safety of the camelization method
        """

        cases = (
            ('camel', 'Camel'),
            ('camel_case', 'CamelCase'),
            ('camel_camel_case', 'CamelCamelCase'),
            ('camel2_camel2_case', 'Camel2Camel2Case'),
            ('get_HTTP_response_code', 'GetHTTPResponseCode'),
            ('get2_HTTP_response_code', 'Get2HTTPResponseCode'),
            ('HTTP_response_code', 'HTTPResponseCode'),
            ('HTTP_response_code_XYZ', 'HTTPResponseCodeXYZ'),
        )

        for test, expected in cases:
            self.assertEqual(camelize(test), expected)

    def test_decamelize(self):
        """
        Test the safety of the decamelization method
        """

        cases = (
            ('Camel', 'camel'),
            ('CamelCase', 'camel_case'),
            ('CamelCamelCase', 'camel_camel_case'),
            ('Camel2Camel2Case', 'camel2_camel2_case'),
            ('getHTTPResponseCode', 'get_http_response_code'),
            ('get2HTTPResponseCode', 'get2_http_response_code'),
            ('HTTPResponseCode', 'http_response_code'),
            ('HTTPResponseCodeXYZ', 'http_response_code_xyz'),
        )

        for test, expected in cases:
            self.assertEqual(decamelize(test), expected)
