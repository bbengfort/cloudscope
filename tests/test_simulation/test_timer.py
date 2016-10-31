# tests.test_simulation.test_timer
# Test the simulation timer functionality for use in Cloudscope.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Mar 10 10:11:58 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_timer.py [5a4cbcc] benjamin@bengfort.com $

"""
Test the simulation timer functionality for use in Cloudscope.
"""

##########################################################################
## Imports
##########################################################################

import simpy
import random
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from cloudscope.simulation.timer import *
from cloudscope.exceptions import SimulationException


##########################################################################
## Simulation Timer Fixtures
##########################################################################

class Callback(object):

    def __init__(self, env):
        self.env       = env
        self.timestamp = None
        self.history   = []
        self.mock_call = mock.Mock()

    def __call__(self, *args, **kwargs):
        self.timestamp = self.env.now
        self.history.append(self.env.now)
        self.mock_call(*args, **kwargs)

    def assert_called_once_with(self, *args, **kwargs):
        self.mock_call.assert_called_once_with(*args, **kwargs)

    def assert_called_at(self, ts, msg=None):
        if msg is None:
            if self.timestamp:
                msg = "Callback last called at {} not at {}".format(self.timestamp, ts)
            else:
                msg = "Callback was not called at any simulation time!"

        assert ts in self.history, msg

    def assert_never_called(self, msg=None):
        if msg is None:
            if self.timestamp:
                msg = "Callback was called at {}!".format(self.timestamp)
            else:
                msg = "Unusual callback state for testing?!"

        assert self.timestamp is None, msg

    def assert_not_called(self, msg=None):
        if msg is None:
            msg = "Callback was called {} times!".format(self.mock_call.call_count)
        return self.assert_call_count(0, msg)

    def assert_call_count(self, count, msg=None):
        if msg is None:
            msg = "Callback was called {} times not {} times!".format(self.mock_call.call_count, count)

        assert count == self.mock_call.call_count, msg


def interrupt(env, timer, after=25, action='stop'):
    """
    Stops the timer after the number of specified time stamps
    """
    while True:
        if env.now >= after:

            action = {
                'stop': timer.stop,
                'reset': timer.reset,
            }[action]

            action()
            break
        yield env.timeout(1)


##########################################################################
## Simulation Timer Tests
##########################################################################

class SimulationTimerTests(unittest.TestCase):
    """
    Tests the Simulation Timer for creating a callback at a specific time.
    """

    def setUp(self):
        self.env = simpy.Environment()

    def tearDown(self):
        self.env = None

    def test_callback(self):
        """
        Test simulation timer callback
        """

        callback = Callback(self.env)
        timer = Timer(self.env, 50, callback)
        timer.start()

        self.env.run(until=100)

        callback.assert_called_once_with()
        callback.assert_called_at(50)

    def test_unstarted_timer(self):
        """
        Assert that unstarted simulation timers aren't called
        """

        callback = Callback(self.env)
        timer = Timer(self.env, 50, callback)

        self.env.run(until=100)

        callback.assert_not_called()
        callback.assert_never_called()

    def test_stopped_timer(self):
        """
        Assert that a timer can be interrupted and not called
        """

        callback = Callback(self.env)
        timer = Timer(self.env, 50, callback)
        timer.start()

        self.env.process(interrupt(self.env, timer))

        self.env.run(until=100)

        callback.assert_not_called()
        callback.assert_never_called()
        self.assertTrue(timer.canceled)

    def test_process_interface(self):
        """
        Assert timers raise an exception when run
        """
        callback = Callback(self.env)
        timer = Timer(self.env, 50, callback)

        with self.assertRaises(SimulationException):
            timer.run()

    def test_timer_state(self):
        """
        Test that a timer maintains its state
        """
        callback = Callback(self.env)
        timer = Timer(self.env, 50, callback)

        def assertion_process(self, env):
            yield env.timeout(1)

            self.assertIsNone(timer.action)
            self.assertFalse(timer.running)
            self.assertFalse(timer.canceled)

            timer.start()
            yield env.timeout(1)

            self.assertIsNotNone(timer.action)
            self.assertTrue(timer.running)
            self.assertFalse(timer.canceled)

            timer.stop()
            yield env.timeout(1)

            self.assertIsNone(timer.action)
            self.assertFalse(timer.running)
            self.assertTrue(timer.canceled)

            yield env.timeout(1)

        self.env.process(assertion_process(self, self.env))
        self.env.run(until=100)

    def test_timer_reset(self):
        """
        Test that a timer can be reset
        """
        callback = Callback(self.env)
        timer = Timer(self.env, 50, callback)
        timer.start()

        self.env.process(interrupt(self.env, timer, action='reset'))

        self.env.run(until=150)

        callback.assert_called_at(75)
        callback.assert_called_once_with()


##########################################################################
## Simulation Interval Tests
##########################################################################

class SimulationIntervalTests(unittest.TestCase):
    """
    Tests the Simulation Timer for creating a callback at a specific time.
    """

    def setUp(self):
        self.env = simpy.Environment()

    def tearDown(self):
        self.env = None

    def test_interval(self):
        """
        Test simulation interval callback
        """

        callback = Callback(self.env)
        timer = Interval(self.env, 20, callback)
        timer.start()

        self.assertTrue(timer.running)
        self.assertFalse(timer.canceled)

        self.env.run(until=100)

        callback.assert_call_count(4)
        callback.assert_called_at(20)
        callback.assert_called_at(40)
        callback.assert_called_at(60)
        callback.assert_called_at(80)

        self.assertTrue(timer.running)
        self.assertFalse(timer.canceled)

    def test_interval_interrupt(self):
        """
        Test simulation interval with interrupt
        """

        callback = Callback(self.env)
        timer = Interval(self.env, 20, callback)
        timer.start()

        self.assertTrue(timer.running)
        self.assertFalse(timer.canceled)

        self.env.process(interrupt(self.env, timer, after=50))
        self.env.run(until=100)

        callback.assert_call_count(2)
        callback.assert_called_at(20)
        callback.assert_called_at(40)
        self.assertTrue(timer.canceled)
        self.assertFalse(timer.running)

    def test_interval_reset(self):
        """
        Test simulation interval with reset
        """

        callback = Callback(self.env)
        timer = Interval(self.env, 20, callback)
        timer.start()

        self.assertTrue(timer.running)
        self.assertFalse(timer.canceled)

        self.env.process(interrupt(self.env, timer, after=50, action='reset'))
        self.env.run(until=125)

        callback.assert_call_count(5)
        callback.assert_called_at(20)
        callback.assert_called_at(40)
        callback.assert_called_at(70)
        callback.assert_called_at(90)
        callback.assert_called_at(110)

        self.assertTrue(timer.canceled)
        self.assertFalse(timer.running)
