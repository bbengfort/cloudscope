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

from .base import Workload, RoutineWorkload

from collections import MutableSequence
from cloudscope.exceptions import WorkloadException


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
