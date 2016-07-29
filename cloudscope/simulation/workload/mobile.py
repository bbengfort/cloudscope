# cloudscope.simulation.workload.mobile
# A workload that simulates a mobile user.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jul 27 14:45:49 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: mobile.py [] benjamin@bengfort.com $

"""
A workload that simulates a single user moving between home, work, and mobile.
"""

##########################################################################
## Imports
##########################################################################

from .base import RoutineWorkload

from collections import defaultdict
from cloudscope.config import settings
from cloudscope.replica import Location, Device
from cloudscope.utils.decorators import memoized
from cloudscope.exceptions import WorkloadException
from cloudscope.dynamo import BoundedNormal, Bernoulli, Discrete


##########################################################################
## Mobile Workload Simulator
##########################################################################

class MobileWorkload(RoutineWorkload):
    """
    This workload extends the RoutineWorkload model by allowing the user to
    switch both locations and devices in a location by specifying two new
    probabilities:

        - Probability of moving locations
        - Probability of switching devices at a location

    This workload is intended to simulate a user moving between work, home,
    and mobile devices in a meaningful way. Note that this means that some
    devices could have "multiple" users generating accesses on them.

    Note that locations and devices are filtered via the settings.
    """

    # Specify what locations are valid to move to.
    invalid_locations = frozenset([
        Location.get(loc) for loc in settings.simulation.invalid_locations
    ])

    # Specify what device types are invalid to switch to.
    invalid_types = frozenset([
        Device.get(dev) for dev in settings.simulation.invalid_types
    ])

    def __init__(self, sim, **kwargs):

        # Distributions to change locations and devices
        self.do_move   = Bernoulli(kwargs.get('move_prob', settings.simulation.move_prob))
        self.do_switch = Bernoulli(kwargs.get('switch_prob', settings.simulation.switch_prob))

        # Initialize the Process
        super(MobileWorkload, self).__init__(sim, **kwargs)

    @memoized
    def locations(self):
        """
        Gets the unique locations of the replicas. Automatically filters
        locations that aren't workable or should be ignored.
        """
        # Create a mapping of locations to replica devices
        locations = defaultdict(list)
        for replica in self.sim.replicas:
            # Filter invalid replicas
            if replica.type in self.invalid_types: continue

            # Filter invalid locations
            if replica.location in self.invalid_locations: continue

            # Associate the location with the replica
            locations[replica.location].append(replica)

        # If no locations exist, then raise a workload error
        if not locations:
            raise WorkloadException(
                "No valid locations or replicas associated with workload!"
            )

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

    def update(self, **kwargs):
        """
        Updates the device and location to simulate random user movement.
        """
        # Update the current object by calling super.
        super(MobileWorkload, self).update(**kwargs)

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
