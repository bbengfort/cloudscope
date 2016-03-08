# tests.test_utils.test_logger
# Testing for the logging utility.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Feb 23 10:10:20 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_logger.py [8d16e6c] benjamin@bengfort.com $

"""
Testing for the logging utility.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.utils.logger import *

try:
    from unittest import mock
except ImportError:
    import mock


##########################################################################
## Logger Tests
##########################################################################

class LoggerTests(unittest.TestCase):
    """
    Basic loger tests.
    """

    def test_wrapped_logger(self):
        """
        Test that the logger is appropriately wrapped.
        """
        logger = WrappedLogger(logger=mock.Mock(), raise_warnings=False, foo='bar')
        calls  = [
            mock.call(10, "This is just a test.", extra={'foo': 'baz'}),
            mock.call(20, "Canaries can fly carrying coconuts.", extra={'foo': 'bar'}),
            mock.call(30, "Beware ducks that dont' blink.", extra={'foo': 'bar'}),
            mock.call(40, "I can't do that, Dave.", extra={'foo': 'bar'}),
            mock.call(50, "The pressure doors are open!", extra={'foo': 'bar'}),
        ]

        logger.debug("This is just a test.", extra={'foo':'baz'}),
        logger.info("Canaries can fly carrying coconuts."),
        logger.warning("Beware ducks that dont' blink."),
        logger.error("I can't do that, Dave."),
        logger.critical("The pressure doors are open!")

        logger.logger.log.assert_has_calls(calls)

    def test_simulation_logger(self):
        """
        Test that the logger is appropriately wrapped.
        """
        env = mock.MagicMock()
        env.now = 42

        logger = SimulationLogger(env, user='bob')
        logger.logger = mock.MagicMock()
        logger.info("testing"),

        logger.logger.log.assert_called_once_with(
            20, "testing", extra={'user': 'bob', 'msgid': 1, 'time': 42}
        )

        logger.info("testing"),

        logger.logger.log.assert_called_with(
            20, "testing", extra={'user': 'bob', 'msgid': 2, 'time': 42}
        )
