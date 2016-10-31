# cloudscope.simulation.workload.cases
# Module that handles specific workload cases for use in the simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Aug 02 15:11:07 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: cases.py [6c96ccc] benjamin@bengfort.com $

"""
Module that handles specific workload cases for use in the simulation.

Currently implemented cases:

- "Best Case" where there are no conflicts (deprecated)
- "Ping Pong" accesses bounce between a set of replicas
- "Tiered" accesses only occur in a single area

"""

##########################################################################
## Imports
##########################################################################

from .base import RoutineWorkload
from .multi import TopologyWorkloadAllocation

from cloudscope.config import settings
from cloudscope.dynamo import CharacterSequence
from cloudscope.dynamo import Bernoulli, Discrete
from cloudscope.exceptions import WorkloadException


##########################################################################
## "Best Case"
##########################################################################

class BestCaseAllocation(TopologyWorkloadAllocation):
    """
    Allocates each device it's own object space by maintaining a static
    reference to an object factory, so that no matter what, replica servers
    get their own object space defined.
    """

    object_factory = CharacterSequence(upper=True)

    def __init__(self, sim, n_objects=None, **defaults):
        """
        Initialize the best case allocation with the number of objects
        per replica server such that no device will get the same object space.

        Allocate can then be called at will with no further parameters.
        """

        super(BestCaseAllocation, self).__init__(sim, **defaults)
        self.n_objects = n_objects or settings.simulation.max_objects_accessed

    def allocate(self, **kwargs):
        """
        Allocates the next device with the next object space.
        """
        objects = [
            self.object_factory.next() for _ in range(self.n_objects)
        ]
        current = Discrete(objects).get()

        # Allocate the workload
        super(BestCaseAllocation, self).allocate(
            objects, current, **kwargs
        )


##########################################################################
## "Ping Pong"
##########################################################################

class PingPongWorkload(RoutineWorkload):
    """
    The ping pong workload shifts a single user between a set of devices such
    that multiple devices access the same object space, but that they do not
    occur at the same time. This is similar to the mobile workload but with
    a more routine bouncing between the specified replicas.
    """

    def __init__(self, sim, devices, **kwargs):
        """
        Instead of specifying a single device for the workload, specify
        multiple devices that we ping pong betweeen with accesses.
        """
        if len(devices) < 2:
            raise WorkloadException(
                "Ping Pong requires at least two devices to play"
            )

        self.players = devices
        self.do_move = Bernoulli(kwargs.get('move_prob', settings.simulation.move_prob))

        kwargs['device'] = Discrete(devices).get()
        super(PingPongWorkload, self).__init__(sim, **kwargs)

    def move(self):
        """
        Moves the workload to a new device
        """
        self.device = Discrete([
            player for player in self.players
            if player != self.device
        ]).get()

    def update(self, **kwargs):
        """
        Updates the device with the possibility of switching devices.
        """
        # Update the current object by calling super.
        super(PingPongWorkload, self).update(**kwargs)

        if self.do_move.get() or self.device is None:
            # Execute the move
            self.move()

            # Log the move
            self.sim.logger.info(
                "{} has moved to {} on {}.".format(
                    self.name, self.location, self.device
                )
            )
