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
from cloudscope.dynamo import CharacterSequence
from cloudscope.utils.decorators import memoized
from cloudscope.utils.timez import humanizedelta
from cloudscope.simulation.base import NamedProcess
from cloudscope.dynamo import BoundedNormal, Bernoulli, Discrete
from cloudscope.exceptions import WorkloadException
from cloudscope.replica import Location, Consistency, Device

from collections import defaultdict
from collections import namedtuple

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
    versions = kwargs.get('objects', settings.simulation.max_objects_accessed)
    if versions > 1:
        return MultiObjectWorkload(env, sim, **kwargs)
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
    valid_locations = frozenset([Location.get(loc) for loc in settings.simulation.valid_locations])
    invalid_types = frozenset([Device.get(dev) for dev in settings.simulation.invalid_types])

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
        self.current   = kwargs.get('current', None)

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
## Multi Object Workload Generator
##########################################################################

class MultiObjectWorkload(Workload):
    """
    Besides the user switching devices and locations, the user also works
    on multiple objects simultaneously in an ordered fashion.
    """

    def __init__(self, env, sim, **kwargs):
        # Get the multi-version specific kwargs and instantiation
        self.do_open = Bernoulli(kwargs.get('object_prob', settings.simulation.object_prob))
        self.factory = kwargs.get('factory', None) or CharacterSequence(upper=True)
        self.objects = kwargs.get('objects', settings.simulation.max_objects_accessed)

        # Initialize the Workload
        super(MultiObjectWorkload, self).__init__(env, sim, **kwargs)

    @property
    def objects(self):
        """
        Objects is a frozenset of names that can be accessed in the workload.
        """
        if not hasattr(self, '_objects'):
            self._objects = frozenset()
        return self._objects

    @objects.setter
    def objects(self, num_or_list):
        """
        You can set a list of object names or a number of objects.
        """

        if isinstance(num_or_list, int):
            # If it's an int, then we want to create a list of objects.
            num_or_list = [
                self.factory.next() for idx in xrange(num_or_list)
            ]

        self._objects = tuple(num_or_list)

    def open(self):
        """
        Like move and switch, this simulates opening a new file.
        """
        if len(self.objects) == 1:
            # There is only one choice, no switching!
            self.current = self.objects[0]
            return False

        self.current = Discrete([
            obj for obj in self.objects
            if obj != self.current
        ]).get()

        return True

    def update(self):
        """
        Updates the device and location to simulate random user movement by
        calling super on the workload version. Also updates the current
        version being worked on by the user.
        """
        # Super call must come first to have a device!
        is_updated = super(MultiObjectWorkload, self).update()

        # Randomly change object to be accessed.
        if self.current is None or self.do_open.get():
            if self.open():
                self.sim.logger.debug(
                    "{} has opened a new object: '{}'".format(
                        self.name, self.current
                    )
                )
                return True

        # No changes made?
        return False or is_updated


##########################################################################
## Traces Workload
##########################################################################

Access = namedtuple("Access", "timestep, replica, object, method")

class TracesWorkload(NamedProcess):
    """
    Deterministic method of providing a workload through traces - a TSV file
    that contains the timestamp, the replica ID, the object name and the
    access method (read/write).
    """

    def __init__(self, path, env, sim, **kwargs):
        self.path = path
        self.sim  = sim

        # Initialize the Process
        super(TracesWorkload, self).__init__(env)

    @memoized
    def name(self):
        return "user {}".format(self._id)

    @memoized
    def devices(self):
        """
        Mapping of replica IDs to device for easy selection.
        """
        return {
            device.id: device
            for device in self.sim.replicas
        }

    def parse(self, line):
        """
        Parses and validates a line from a traces file.
        """
        # Parse the line, splitting on whitespace
        line = line.strip().split()

        # If no object is specified, insert None
        if len(line) == 3:
            line.insert(2, None)

        # Validate the length
        if len(line) != 4:
            raise WorkloadException(
                "Unparsable line: '{}'".format(" ".join(line))
            )

        # Validate the access
        if line[3] not in {READ, WRITE}:
            raise WorkloadException(
                "Unknown access '{}' must be read or write".format(line[3])
            )

        # Parse the various fields
        line[0] = int(float(line[0]))
        line[3] = line[3].lower()

        return Access(*line)

    def accesses(self):
        """
        Reads the traces and yields the access tuple. Assumes a file format:

            timestep    replica    object    method

        If the row is length three instead of length for a None is inserted
        for the object in the 2nd position.
        """
        with open(self.path, 'r') as fobj:
            for line in fobj:
                yield self.parse(line)

    def run(self):
        """
        Reads in the accesses (which must be ordered by timestep) and updates
        the environment with delays and calls as required.
        """
        clock = 0 # maintain the time since last access

        # read through accesses in an ordered fashion.
        for access in self.accesses():

            # validate that the access occurs now or at the clock
            if access.timestep < clock:
                raise WorkloadException(
                    "Unordered access '{}' occurred at clock {}".format(access, clock)
                )

            # wait until timestep for access occurs
            wait = access.timestep - clock
            yield self.env.timeout(wait)
            clock = self.env.now

            # get the appropriate device to trigger the access
            device = self.devices.get(access.replica, None)

            # ensure that the device exists
            if device is None:
                raise WorkloadException(
                    "Unknown device with replica id '{}'".format(access.replica)
                )

            # perform the access
            if access.method == READ:
                device.read(access.object)

            if access.method == WRITE:
                device.write(access.object)

            # record the access to the results timeseries
            self.sim.results.update(
                access.method, (device.id, device.location, self.env.now)
            )

            # debug log the read/write access
            self.sim.logger.debug(
                "{} access by {} on {} (at {}) after {}".format(
                    access.method, self.name, device, device.location,
                    humanizedelta(milliseconds=wait)
                )
            )
