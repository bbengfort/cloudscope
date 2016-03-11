# cloudscope.simulation.timer
# Implements a timer process for SimPy simulations.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 09:00:19 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: timer.py [6a38557] benjamin@bengfort.com $

"""
Implements a timer process for SimPy simulations. See:
http://stackoverflow.com/questions/35202982/how-do-i-interrupt-or-cancel-a-simpy-timeout-event
"""

##########################################################################
## Imports
##########################################################################

import simpy

from .base import Process
from cloudscope.exceptions import SimulationException

##########################################################################
## Timer Process
##########################################################################

class Timer(Process):
    """
    A Timer is a process that waits a certain amount of time then calls a
    callback. Timers, unlike timeouts, can be interupted (because it wraps a
    process), and reset (stopped, then started). Intervals are easily created
    by simply calling start after the timer has been stopped.

    Note that while this is a `Process` (for type checking) it doesn't init
    an action using a run method as normal subclasses might.
    """

    def __init__(self, env, delay, callback):
        self.env      = env
        self.delay    = delay
        self.action   = None
        self.callback = callback
        self.running  = False
        self.canceled = False

    def wait(self):
        """
        Calls a callback after time has elapsed.
        """
        try:
            yield self.env.timeout(self.delay)
            self.callback()
        except simpy.Interrupt as i:
            self.canceled = True

        self.running = False

    def start(self):
        """
        Starts the timer
        """
        if not self.running:
            self.running  = True
            self.canceled = False
            self.action   = self.env.process(self.wait())
        return self.action

    def stop(self):
        """
        Stops the timer
        """
        if self.running:
            self.action.interrupt()
            self.action   = None
        return self.action

    def reset(self):
        """
        Interupts the current timer and starts/returns a completely new timer
        with the same properties as the current timer. Kind of a hack, but it
        works!
        """
        self.stop()

        timer = self.__class__(self.env, self.delay, self.callback)
        timer.start()

        return timer

    def run(self):
        raise SimulationException(
            "Timers cannot be run, they should be started and stopped!"
        )


##########################################################################
## Interval Process
##########################################################################

class Interval(Timer):
    """
    An interval is a process that simply schedules itself again after the
    callback is executed. It can be stopped, started, and restarted normally.
    """

    def wait(self):
        """
        Calls a callback after time has elapsed.
        """
        while True:
            try:
                yield self.env.timeout(self.delay)
                self.callback()
            except simpy.Interrupt as i:
                self.canceled = True
                self.running = False
                break
