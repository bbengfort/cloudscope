# cloudscope.simulation.workload.conflict
# A workload allocation scheme that manages the amount of potential conflict.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Aug 03 10:53:39 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: conflict.py [015df0f] benjamin@bengfort.com $

"""
A workload allocation scheme that manages the amount of potential conflict,
defined as the amount of overlap between objects allocated to each device.
"""

##########################################################################
## Imports
##########################################################################

import warnings

from .base import RoutineWorkload
from .multi import TopologyWorkloadAllocation
from .multi import RANDOM_SELECT, ROUNDS_SELECT

from cloudscope.config import settings
from cloudscope.utils.decorators import setter
from cloudscope.dynamo import CharacterSequence
from cloudscope.exceptions import WorkloadWarning
from cloudscope.exceptions import WorkloadException
from cloudscope.exceptions import ImproperlyConfigured
from cloudscope.dynamo import Bernoulli, Discrete, Uniform

from collections import defaultdict


##########################################################################
## ConflictWorkloadAllocation
##########################################################################


class ConflictWorkloadAllocation(TopologyWorkloadAllocation):
    """
    A specialized workload allocation that will be the default in simulations
    when not using a trace file or other specialized hook. This allocation
    does not allow users to "move" or "switch" devices as in the original
    mobile workloads. Instead, each user is assigned to a location using a
    specific strategy and generates routine workload accesses.

    Conflict is defined by a likelihood and specifies how objects are assigned
    to users for routine accesses. A conflict likelihood of 1 means the exact
    same objects are assigned to all users. A conflict of zero means that no
    objects will overlap for any of the users.
    """

    workload_class = RoutineWorkload
    object_factory = CharacterSequence(upper=True)

    def __init__(self, sim, n_objects=None, conflict_prob=None,
                 loc_max_users=None, **defaults):
        """
        Initialize the conflict workload allocation with the following params:

            - n_objects: number of objects per user (constant or range)
            - conflict_prob: the likelihood of assigning an object to multiple replicas
            - loc_max_users: the maximum users per location during allocation

        Workloads are allocated to each location in a round robin fashion up
        to the maximum number of users or if the location maximum limits are
        reached (or no devices remain to allocate to).
        """

        # Initialize the topology workload
        super(ConflictWorkloadAllocation, self).__init__(sim, **defaults)

        # Initialize parameters or get from settings
        self.n_objects = n_objects
        self.loc_max_users =  loc_max_users
        self.do_conflict = Bernoulli(conflict_prob or settings.simulation.conflict_prob)

        # Reorganize the devices into locations tracking the location index
        # as well as how many users are assigned to each location via a map.
        self.locidx    = 0
        self.locations = {device.location: 0 for device in self.devices}
        self.devices   = {
            location: [
                device for device in self.devices if device.location == location
            ] for location in self.locations.keys()
        }

    @setter
    def n_objects(self, value):
        """
        Creates a uniform probability distribution for the given value. If the
        value is an integer, then it will return that value constantly. If it
        is a range, it will return the uniform distribution.

        If the value is None, it will look the value up in the configuration.
        """
        value = value or settings.simulation.max_objects_accessed

        if isinstance(value, int):
            return Uniform(value, value)

        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ImproperlyConfigured(
                    "Specify the number of objects as a range: (min, max)"
                )
            return Uniform(*value)

        else:
            raise ImproperlyConfigured(
                "Specify the number of objects as a constant "
                "or uniform random range."
            )

    @setter
    def loc_max_users(self, value):
        """
        Creates a uniform probability distribution for the given value. If the
        value is an integer, then it will return that value constantly. If it
        is a range, it will return the uniform distribution.

        If the value is None, it will look the value up in the configuration.
        """
        value = value or settings.simulation.max_users_location

        if value is None: return None

        if isinstance(value, int):
            return Uniform(value, value)

        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ImproperlyConfigured(
                    "Specify the max users per location as a range: (min, max)"
                )
            return Uniform(*value)

        else:
            raise ImproperlyConfigured(
                "Specify the maximum number of users per location as a "
                "constant or uniform random range (or None)."
            )

    def select(self, attempts=0):
        """
        Make a device selection by assigning the users in a round robin
        """
        # Get the current location and update the location index.
        location = self.locations.keys()[self.locidx]

        # Update the location index to go around the back end
        self.locidx += 1
        if self.locidx >= len(self.locations.keys()):
            self.locidx = 0

        # Test to see if we have any locations left
        if not self.devices[location]:
            if attempts > len(self.locations.keys()):
                raise WorkloadException(
                    "Cannot select device for allocation, no devices left!"
                )
            return self.select(attempts + 1)

        # Test to see if we have reached the location limit
        if self.loc_max_users is not None:
            # TODO: Change this so that the users is randomly allocated in
            # advance rather than on the fly with different selections per
            # area (e.g. fix the random allocations per location).
            if self.locations[location] >= self.loc_max_users.get():
                if attempts > len(self.locations.keys()):
                    raise WorkloadException(
                        "Cannot allocate any more users, "
                        "max users per location reached!"
                    )
                return self.select(attempts + 1)

        # We will definitely make a selection for this location below here
        # so increment the location selection count to limit allocation.
        self.locations[location] += 1

        # Round robin device selection from the location
        if self.selection == ROUNDS_SELECT:
            return self.devices[location].pop()

        # Random device selection from the location
        if self.selection == RANDOM_SELECT:
            device = Discrete(self.devices[location]).get()
            self.devices[location].remove(device)
            return device

        # How did we end up here?!
        raise WorkloadException(
            "Unable to select a device for allocation!"
        )

    def allocate(self, objects=None, current=None, **kwargs):
        """
        Allocate is overriden here to provide a warning to folks who call it
        directly -- it will simply call super (allocating the next device with
        the specified object space) and it WILL NOT maintain the conflict
        object distribution.

        Instead, it is preferable to call allocate_many with the number of
        users that you wish to allocate, and in fact - to only do it once!
        """
        warnings.warn(WorkloadWarning(
            "Conflict space is not allocated correctly! "
            "This function will allocate a device from the topology with the "
            "specified objects but will not maintain the conflict likelihood."
            " Use allocate_many to correctly allocate using this class."
        ))

        super(ConflictWorkloadAllocation, self).allocate(objects, current, **kwargs)

    def allocate_many(self, n_users, **kwargs):
        """
        This is the correct entry point for allocating users with different
        conflict probability per object across the simulation. It assigns
        an object space to n_users by allocating every object from the
        object factory to users in a round robin fashion with the given
        conflict probabilty.
        """

        # Define the maximum number of objects per user.
        max_user_objects = {
            idx: self.n_objects.get() for idx in range(n_users)
        }

        # Define each user's object space
        object_space = [[] for _ in range(n_users)]

        # Start allocating objects to the users in a round robin fashion.
        for _ in range(sum(max_user_objects.values())):

            # Get the next object as a candidate for assignment
            obj = self.object_factory.next()
            assigned = False

            # Go through each user and determine if we should assign.
            for idx, space in enumerate(object_space):
                # If this space is already full, carry on.
                if len(space) >= max_user_objects[idx]:
                    continue

                # If the object is not assigned, or on conflict probabilty,
                # Then assign the object to that particular object space.
                if not assigned or self.do_conflict.get():
                    space.append(obj)
                    assigned = True

            # If we've gotten to the end without assignment, we're done!
            if not assigned: break

        # Now go through and allocate all the workloads
        for objects in object_space:
            device  = self.select()
            current = Discrete(objects).get()
            extra   = self.defaults.copy()
            extra.update(kwargs)

            self.workloads.append(
                self.workload_class(
                    self.sim, device=device, objects=objects, current=current, **extra
                )
            )
