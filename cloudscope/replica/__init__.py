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
from .federated import StentorEventualReplica

from cloudscope.config import settings
from cloudscope.exceptions import ImproperlyConfigured

##########################################################################
## Type Factory
##########################################################################

ReplicaTypes = {

    'default': {
        Consistency.STRONG: RaftReplica,
        Consistency.EVENTUAL: EventualReplica,
        Consistency.STENTOR: StentorEventualReplica,
        Consistency.TAG: TagReplica,
        Consistency.RAFT: RaftReplica,
    },

    'tiered': {
        Consistency.STRONG: TieredRaftReplica,
    },

    'floated': {
        Consistency.STRONG: FloatedRaftReplica,
    },

    'federated': {
        Consistency.STRONG: FederatedRaftReplica,
        Consistency.EVENTUAL: FederatedEventualReplica,
        Consistency.STENTOR: StentorEventualReplica,
        Consistency.RAFT: FederatedRaftReplica,
    },
}

def replica_factory(simulation, **kwargs):
    """
    Factory to create a replica with the correct type, based on consistency.
    """
    # Determine the consistency level of the simulation
    consistency = Consistency.get(kwargs.get(
        'consistency', settings.simulation.default_consistency
    ))

    # Determine the integration level of the simulation
    integration = settings.simulation.integration
    if integration not in ReplicaTypes:
        raise ImproperlyConfigured(
            'Integration "{}" not recognized, use one of {}'.format(
                integration, ", ".join(ReplicaTypes.keys())
            )
        )

    # Check that the desired consistenty matches the integration level
    # If not fall back to the default replica type with a warning
    if consistency not in ReplicaTypes[integration]:
        simulation.logger.warn(
            'Consistency level "{}" not implemented in {}'.format(
                consistency, integration
            )
        )
        integration = 'default'

    # Return a replica with the given consistency level for the integration.
    return ReplicaTypes[integration][consistency](simulation, **kwargs)
