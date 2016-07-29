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

from cloudscope.config import settings
from cloudscope.dynamo import CharacterSequence

##########################################################################
## Factory Function
##########################################################################

def create(env, sim, **kwargs):
    """
    Returns the correct workload class depending on synchronous or async
    accesses, multiple objects or not, and whether or not a trace exists.

    Returns a single workload; to generate multiple workloads, must generate.
    """
    # Create a manual trace if it's passed in
    trace = kwargs.get('trace', None)
    if trace:
        if settings.simulation.synchronous_access:
            return SynchronousTracesWorkload(trace, env, sim)
        else:
            return TracesWorkload(trace, sim)


    # Otherwise construct random workload generator
    objects = kwargs.pop('objects', settings.simulation.max_objects_accessed)
    factory = CharacterSequence(upper=True)
    objects = [
        factory.next() for _ in range(objects)
    ]
    import random
    device = random.choice(sim.replicas)
    return MobileWorkload(sim, device=device, objects=objects, **kwargs)
