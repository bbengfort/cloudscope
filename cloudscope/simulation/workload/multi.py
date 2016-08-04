# cloudscope.simulation.workload.multi
# Wrapper for multiple workloads (e.g. multiple users) as a collection.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Aug 02 14:19:48 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: multi.py [] benjamin@bengfort.com $

"""
Wrapper for multiple workloads (e.g. multiple users) as a collection.

This is the primary view that the simulation sees of the workload: a
collection of one or more workloads wrapped in the WorkloadCollection object.
The WorkloadCollection specifically maps workload objects to a topology and
can enforce rules like only one user on a device at a time, etc.
"""

##########################################################################
## Imports
##########################################################################

from .base import Workload
from .base import RoutineWorkload

from cloudscope.dynamo import Discrete
from cloudscope.config import settings
from cloudscope.dynamo import CharacterSequence
from cloudscope.exceptions import WorkloadException

from copy import copy
from collections import MutableSequence


##########################################################################
## Module Constants
##########################################################################

RANDOM_SELECT = 'random'
ROUNDS_SELECT = 'rounds'

SELECTION_STRATEGIES = (
    RANDOM_SELECT, ROUNDS_SELECT,
)


##########################################################################
## Base Workload Collection
##########################################################################

class WorkloadCollection(MutableSequence):
    """
    The base collection of workloads, this doesn't do anything special except
    support the interaction with multiple workloads at once.
    """

    def __init__(self, *workloads):
        """
        Pass in a list of workloads to collect together as intial arguments.
        """
        # Internal container for holding workloads
        self.workloads = list(workloads)

    def __getitem__(self, idx):
        return self.workloads[idx]

    def __setitem__(self, idx, workload):
        self.workloads[idx] = workload

    def __delitem__(self, idx):
        del self.workloads[idx]

    def __len__(self):
        return len(self.workloads)

    def __str__(self):

        # Get the types of workloads this object contains
        types = set(type(workload).__name__ for workload in self)
        return "Collection of {} Workloads ({} types)".format(len(self), len(types))

    def insert(self, idx, workload):
        self.workloads.insert(idx, workload)


##########################################################################
## Workload Allocator
##########################################################################

class WorkloadAllocation(WorkloadCollection):
    """
    A class that allocates multiple workloads based on passed in parameters.
    For example, this allocator can allocate identical workloads for a
    specific number of users, or it can do something more complex.

    Note that since it has knowledge of the internal workloads, it can be
    used to do conflict free workload allocation, etc.
    """

    workload_class = RoutineWorkload

    def __init__(self, sim, **defaults):
        """
        The allocator accepts a simulation and default arguments for all
        workloads that are allocated using the allocate method. Any args that
        should not be passed to Workload objects should be popped.
        """
        # Create the internal workloads wrapper
        super(WorkloadAllocation, self).__init__()

        # Set the properties on the workload
        self.sim      = sim
        self.defaults = defaults

    def allocate(self, device=None, objects=None, current=None, **kwargs):
        """
        The allocate method takes approximately the same parameters required
        to instantiate a single Workload object. Note that the kwargs will be
        updated with the defaults passed into the allocation method.
        """

        # Create the keyword arguments for the Workload
        extra = self.defaults.copy()
        extra.update(kwargs)

        self.workloads.append(
            self.workload_class(
                self.sim, device=device, objects=objects, current=current, **extra
            )
        )

    def allocate_many(self, num, **kwargs):
        """
        Allocate a specific number of best case devices.
        """
        for _ in range(num):
            self.allocate(**kwargs)


##########################################################################
## Topological Workload Allocator
##########################################################################

class TopologyWorkloadAllocation(WorkloadAllocation):
    """
    Automatically allocates devices from the simulation topology using the
    specified allocation strategy. The device selection strategy is a
    string that can be one of:

        - random: randomly choose a device without replacement
        - rounds: choose devices in order until none are left

    Allocate can be called with no devie as a result.
    """

    def __init__(self, sim, selection=ROUNDS_SELECT, **defaults):
        """
        Initialize with the simulation that contains the topology as well as
        the device selection strategy which can be either random or rounds.
        """
        if selection not in SELECTION_STRATEGIES:
            raise WorkloadException(
                "'{}' not a valid selection strategy, choose from {}".format(
                    selection, ", ".join(SELECTION_STRATEGIES)
                )
            )

        self.selection = selection
        self.devices   = copy(sim.replicas)
        super(TopologyWorkloadAllocation, self).__init__(sim, **defaults)

    def select(self):
        """
        Make a device selection based on the selection strategy
        """
        if self.selection == ROUNDS_SELECT:
            return self.devices.pop()

        if self.selection == RANDOM_SELECT:
            device = Discrete(self.devices).get()
            self.devices.remove(device)
            return device

    def allocate(self, objects=None, current=None, **kwargs):
        """
        Allocate automatically selects a device using the selection strategy.
        """
        # Allocate a device if not passed in.
        device = kwargs.pop('device', None) or self.select()

        super(TopologyWorkloadAllocation, self).allocate(
            device, objects, current, **kwargs
        )
