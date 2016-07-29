# cloudscope.simulation.workload.synchronous
# Synchronous workloads for testing simulation timing.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jul 27 15:55:02 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: synchronous.py [] benjamin@bengfort.com $

"""
Synchronous workloads for testing simulation timing.
"""

##########################################################################
## Imports
##########################################################################

from .base import Workload
from .base import RoutineWorkload
from .mobile import MobileWorkload
from .traces import TracesWorkload

##########################################################################
## TODO: Convert to a mixin and adapt classes in real time?
##########################################################################

class SynchronousWorkload(Workload):
    """
    Converts a workload into synchronous access, meaning that an access must
    wait until the previous access is complete (or dropped) until the next
    access can be issued.

    The mixin does this by overriding `trigger_access` and creates a callback
    mechanism if there is still an access underway.
    """

    def __init__(self, *args, **kwargs):
        super(SynchronousWorkload, self).__init__(*args, **kwargs)

    def access(self):
        raise NotImplementedError(
            "Synchronous single object workload is not yet implemented."
        )


class SynchronousTracesWorkload(TracesWorkload):
    """
    Converts a traces workload into synchronous access, meaning that an
    access must wait until the previous access is complete (or dropped) until
    the next access can be issued.

    The mixin does this by overriding `trigger_access` and creates a callback
    mechanism if there is still an access underway.
    """

    def __init__(self, *args, **kwargs):
        super(SynchronousTracesWorkload, self).__init__(*args, **kwargs)

    def access(self):
        raise NotImplementedError(
            "Synchronous multiple object workload is not yet implemented."
        )
