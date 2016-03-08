# cloudscope.simulation.workload
# Defines the generators that create versions or "work" in the simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 08:43:19 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: workload.py [b9507c0] benjamin@bengfort.com $

"""
Defines the generators that create versions or "work" in the simulation.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.simulation.base import NamedProcess
from cloudscope.dynamo import BoundedNormal, Bernoulli, Discrete
from cloudscope.utils.decorators import memoized
from cloudscope.replica import Location, Replica, Version
from cloudscope.exceptions import UnknownType
from cloudscope.utils.timez import humanizedelta

from collections import defaultdict


##########################################################################
## Module Constants
##########################################################################

READ  = "read"
WRITE = "write"

##########################################################################
## Factory Function
##########################################################################

def create(env, sim, **kwargs):
    """
    Returns the Workload or MultiVersionWorkload depending on the number of
    versions that are being managed by the simulation.
    """
    versions = kwargs.get('versions', settings.simulation.max_objects_accessed)
    if versions > 1:
        return MultiVersionWorkload(env, sim, **kwargs)
    return Workload(env, sim, **kwargs)

##########################################################################
## Initial Workload Generator
##########################################################################

class Workload(NamedProcess):
    """
    Represents a single user that is moving around and accessing devices by
    making reads and writes to the simulation.
    """

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

        # Current device, and location
        self.location  = None
        self.device    = None
        self.current   = kwargs.get('version', None)

        # Access interval for the version.
        self.next_access = BoundedNormal(
            kwargs.get('access_mean', settings.simulation.access_mean),
            kwargs.get('access_stddev', settings.simulation.access_stddev),
            floor = 0.0,
        )

        # Initialize the Process
        super(Workload, self).__init__(env)

    @memoized
    def name(self):
        return "user {}".format(self._id)

    @memoized
    def locations(self):
        """
        Gets the unique locations of the replicas. Automatically filters
        locations that aren't workable or should be ignored.
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
            self.switch()
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
                    "{} has moved to {} on their {}.".format(
                        self.name, self.location, self.device
                    )
                )
                return True
            return False

        if self.do_switch.get() or self.device is None:
            if self.switch():
                self.sim.logger.debug(
                    "{} has switched devices to their {} ({})".format(
                        self.name, self.device, self.location
                    )
                )
                return True
            return False

        return False

    def run(self):

        # Initialze location and device
        self.update()

        while True:
            # Wait for the next access interval
            wait = self.next_access.get()
            yield self.env.timeout(wait)

            # Initiate an access after the interval is complete.
            access = READ if self.do_read.get() else WRITE
            # Log timeseries
            self.sim.results.update(
                access, (self.device.id, self.location, self.env.now)
            )

            if access == WRITE:
                # Write to the current version (e.g. fork it)
                self.device.write(self.current)

            if access == READ:
                # Read the latest version of the current object
                self.device.read(self.current)

            # Debug log the read/write access
            self.sim.logger.debug(
                "{} access by {} on {} (at {}) after {}".format(
                    access, self.name, self.device, self.location,
                    humanizedelta(milliseconds=wait)
                )
            )

            # Update the state (e.g. device/location) of the workload
            self.update()


##########################################################################
## Multi Version Workload Generator
##########################################################################

class MultiVersionWorkload(Workload):
    """
    Besides the user switching devices and locations, the user also works
    on multiple objects simultaneously in an ordered fashion.
    """

    def __init__(self, env, sim, **kwargs):
        # Get the multi-version specific kwargs and instantiation
        self.versions = kwargs.get('versions', settings.simulation.max_objects_accessed)
        self.do_open  = Bernoulli(kwargs.get('object_prob', settings.simulation.object_prob))

        # Initialize the Workload
        super(MultiVersionWorkload, self).__init__(env, sim, **kwargs)

    @property
    def versions(self):
        if not hasattr(self, '_versions'):
            self._versions = []
        return self._versions

    @versions.setter
    def versions(self, num_or_list):
        """
        You can set a list of versions or a number of versions.
        """
        if isinstance(num_or_list, int):
            # If it's an int, then we want to create a list of versions.
            num_or_list = [None for _ in xrange(num_or_list)]

        # Set the internal versions to the passed in list.
        self._versions = num_or_list

    def open(self):
        """
        Like move and switch, this simulates opening a new file.
        """
        if len(self.versions) == 1 or not filter(None, self.versions):
            # There is only one choice, no switching!
            self.current = self.versions[0]
            return False

        self.current = Discrete([
            version for version in self.versions
            if version is not self.current
        ]).get()

        return True

    def update(self):
        """
        Updates the device and location to simulate random user movement by
        calling super on the workload version. Also updates the current
        version being worked on by the user.
        """
        super(MultiVersionWorkload, self).update()
        if self.do_open.get() or self.current is None:
            if self.open():
                self.sim.logger.debug(
                    "{} has opened a new version {}".format(
                        self.name, self.current
                    )
                )
                return True
        return False
