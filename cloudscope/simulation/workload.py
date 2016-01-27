# cloudscope.simulation.workload
# Defines the generators that create versions or "work" in the simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 08:43:19 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: cloudscope.simulation.workload.py [] benjamin@bengfort.com $

"""
Defines the generators that create versions or "work" in the simulation.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.simulation.base import Process
from cloudscope.dynamo import BoundedNormal, Bernoulli, Discrete
from cloudscope.utils.decorators import memoized
from cloudscope.simulation.replica import Location, Replica, Version
from cloudscope.exceptions import UnknownType
from cloudscope.utils.timez import humanizedelta

from collections import defaultdict


##########################################################################
## Module Constants
##########################################################################

READ  = "read"
WRITE = "write"

##########################################################################
## Initial Workload Generator
##########################################################################

class Workload(Process):

    # TODO: add this to settings rather than hard code.
    valid_locations = frozenset(settings.simulation.valid_locations)
    invalid_types = frozenset(settings.simulation.invalid_types)

    def __init__(self, env, sim, **kwargs):
        # Parent
        self.sim = sim

        # Various workload probabilities
        self.do_move   = Bernoulli(kwargs.get('move_prob', settings.simulation.move_prob))
        self.do_switch = Bernoulli(kwargs.get('switch_prob', settings.simulation.switch_prob))
        self.do_read   = Bernoulli(kwargs.get('read_prob', settings.simulation.read_prob))

        # Current Device and location
        self.location  = None
        self.device    = None
        self.version   = None

        # Access interval for the version.
        self.next_access = BoundedNormal(
            kwargs.get('access_mean', settings.simulation.access_mean),
            kwargs.get('access_stddev', settings.simulation.access_stddev),
            floor = 0.0,
        )

        # Initialize the Process
        super(Workload, self).__init__(env)

    @memoized
    def locations(self):
        """
        Gets the unique locations of the replicas. Automatically filters
        locations that aren't workable or
        """
        locations = defaultdict(list)
        for replica in self.sim.replicas:
            if replica.location in self.valid_locations:
                if replica.type not in self.invalid_types:
                    locations[replica.location].append(replica)
        return locations

    def move(self):
        """
        Moves the user to a new location
        """
        if len(self.locations) == 1:
            # There is only one choice, no switching!
            self.location = self.locations.keys()[0]
            return False

        self.location = Discrete([
            location  for location in self.locations.keys()
            if location != self.location
        ]).get()

        self.switch()
        return True

    def switch(self):
        """
        Switches the device the user is currently working on
        """
        if len(self.locations[self.location]) == 1:
            # There is only one choice, no switching!
            self.device = self.locations[self.location][0]
            return False

        self.device = Discrete([
            device for device in self.locations[self.location]
            if device != self.device
        ]).get()

        return True

    def update(self):
        """
        Updates the device and location to simulate random user movement.
        """
        if self.do_move.get() or self.location is None:
            if self.move():
                self.sim.logger.info(
                    "User has moved to {} on their {}.".format(
                        self.location, self.device
                    )
                )
                return True
            return False

        if self.do_switch.get() or self.device is None:
            if self.switch():
                self.sim.logger.info(
                    "User has switched devices to their {} ({})".format(
                        self.device, self.location
                    )
                )
                return True
            return False

        return False

    def run(self):

        # Initialze location, device, and version
        self.update()
        self.version = Version(self.device)
        self.device.broadcast(self.version)

        while True:
            # Wait for the next access interval
            wait = self.next_access.get()
            yield self.env.timeout(wait)

            # Initiate an access after the interval is complete.
            access = READ if self.do_read.get() else WRITE

            if access == WRITE:
                # TODO: Perform appropriate device write
                self.version = self.version.fork(self.device)
                self.device.broadcast(self.version)

                # Log timeseries
                self.sim.results.update(
                    WRITE, (self.env.now, self.location, self.device.label)
                )

            if access == READ:
                # TODO: Perform appropriate device read

                # Log timeseries
                self.sim.results.update(
                    READ, (self.env.now, self.location, self.device.label)
                )

            # Debug log the read/write access
            self.sim.logger.debug(
                "{} access by {} (at {}) after {}".format(
                    access, self.device, self.location,
                    humanizedelta(milliseconds=wait)
                )
            )

            # Update the state (e.g. device/location) of the workload
            self.update()
