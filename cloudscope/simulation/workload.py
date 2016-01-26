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

import random

from cloudscope.config import settings
from cloudscope.simulation.base import Process
from cloudscope.dynamo import Normal, Bernoulli, Discrete
from cloudscope.utils.decorators import memoized
from cloudscope.simulation.replica import Location, Replica
from cloudscope.exceptions import UnknownType

from collections import defaultdict

##########################################################################
## Initial Workload Generator
##########################################################################

class Workload(Process):

    # TODO: add this to settings rather than hard code.
    valid_locations = frozenset([Location.HOME, Location.WORK, Location.MOBILE])
    invalid_types = frozenset([Replica.STORAGE])

    def __init__(self, env, sim, **kwargs):
        self.sim = sim
        self.do_move   = Bernoulli(0.2).get
        self.do_switch = Bernoulli(0.4).get

        # Current Device and location
        self.location  = None
        self.device    = None

        # Write Likelihood of a Device
        # About 20 writes per hour with stddev of about 8 writes per hour.
        self.write_wait = Normal(180000, 51429)

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
        if self.do_move() or self.location is None:
            return self.move()

        if self.do_switch() or self.device is None:
            return self.switch()

        return False

    def run(self):
        from cloudscope.utils.timez import humanizedelta
        self.update()
        self.sim.logger.debug(
            "User is at {} on their {}".format(
                self.location, self.device
            )
        )

        while True:
            self.update()
            wait = self.write_wait.get()
            yield self.env.timeout(wait)

            self.sim.logger.debug(
                "User is at {} on their {} (after {})".format(
                    self.location, self.device, humanizedelta(milliseconds=wait)
                )
            )
