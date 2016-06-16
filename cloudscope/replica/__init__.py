# cloudscope.replica
# Functionality for different replica types in the cloud storage system.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 06:47:26 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [] benjamin@bengfort.com $

"""
Functionality for different replica types in the cloud storage system.
"""

##########################################################################
## Imports
##########################################################################

from .base import *
from .store import *
from .access import *
from .consensus import RaftReplica
from .consensus import TagReplica
from .consensus import FloatedRaftReplica
from .consensus import TieredRaftReplica
from .eventual import EventualReplica
from .federated import FederatedRaftReplica
from .federated import FederatedEventualReplica

from cloudscope.config import settings

##########################################################################
## Type Factory
##########################################################################

ReplicaTypes = {
    # Consistency.STRONG: RaftReplica,
    # Consistency.STRONG: TieredRaftReplica,
    # Consistency.STRONG: FloatedRaftReplica,
    Consistency.MEDIUM: TagReplica,
    # Consistency.LOW: EventualReplica,

    Consistency.STRONG: FederatedRaftReplica,
    Consistency.LOW: FederatedEventualReplica,
}

def replica_factory(simulation, **kwargs):
    """
    Factory to create a replica with the correct type, based on consistency.
    """
    consistency = Consistency.get(kwargs.get(
        'consistency', settings.simulation.default_consistency
    ))
    return ReplicaTypes[consistency](simulation, **kwargs)
