# cloudscope.simulation.workload
# Defines simulation processes that generate "work", e.g. accesses.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jul 27 10:21:57 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [b9507c0] benjamin@bengfort.com $

"""
Defines simulation processes that generate "work", e.g. accesses.
"""

##########################################################################
## Imports
##########################################################################

from .base import Workload
from .base import RoutineWorkload
from .traces import TracesWorkload
from .mobile import MobileWorkload
from .cases import PingPongWorkload

from .multi import WorkloadCollection
from .multi import WorkloadAllocation
from .cases import BestCaseAllocation
from .multi import TopologyWorkloadAllocation
from .conflict import ConflictWorkloadAllocation

from cloudscope.config import settings

##########################################################################
## Factory Function
##########################################################################

def create(sim, **kwargs):
    """
    Returns the correct workload for the simulation. There are currently two
    possible workloads to return depending on the kwargs:

        - Load the accesses from a trace file
        - Create a conflict/topology allocating workload for n users.

    See the workload allocation objects for more information.
    """
    # Create a manual trace if it's passed in
    trace = kwargs.pop('trace', None)
    if trace:
        if settings.simulation.synchronous_access:
            raise NotImplementedError(
                "Synchronous workloads not implemented yet"
            )
        else:
            return TracesWorkload(trace, sim)

    # Otherwise construct a conflict generation workload.
    users = kwargs.pop('users', settings.simulation.users)
    workload = ConflictWorkloadAllocation(sim, **kwargs)
    workload.allocate_many(users)
    return workload
