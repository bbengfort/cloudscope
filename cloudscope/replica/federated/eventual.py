# cloudscope.replica.federated.eventual
# Implements eventual (low) consistency and high availability.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jun 15 22:05:29 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: eventual.py [] benjamin@bengfort.com $

"""
Implements eventual (low) consistency and high availability.
"""

##########################################################################
## Imports
##########################################################################

import random

from cloudscope.config import settings
from cloudscope.replica import Consistency
from cloudscope.replica.eventual import EventualReplica


##########################################################################
## Module Constants
##########################################################################

## Fetch simulation settings from defaults
SYNC_PROB  = settings.simulation.sync_prob
LOCAL_PROB = settings.simulation.local_prob


##########################################################################
## Federated Eventual Replica
##########################################################################

class FederatedEventualReplica(EventualReplica):

    def __init__(self, simulation, **kwargs):
        super(FederatedEventualReplica, self).__init__(simulation, **kwargs)

        # Federated settings
        self.sync_prob    = kwargs.get('anti_entropy_delay', SYNC_PROB)
        self.local_prob   = kwargs.get('do_gossip', LOCAL_PROB)

    def get_anti_entropy_neighbor(self):
        """
        Selects a neighbor to perform anti-entropy with, prioritizes local
        neighbors over remote ones and also actively selects the sequential
        consistency nodes to perform anti-entropy with.
        """
        # Decide if we should sync with the core consensus group
        if random.random() <= self.sync_prob:

            # Find a strong consensus node that is local
            neighbors = [
                node for node in self.neighbors(consistency=Consistency.STRONG)
                if node.location == self.location
            ]

            # If we have local nodes, choose one of them
            if neighbors: return random.choice(neighbors)

            # Otherwise choose any strong node that exists
            neighbors = self.neighbors(consistency=Consistency.STRONG)
            if neighbors: return random.choice(neighbors)

        # Decide if we should do anti-entropy locally or across the wide area.
        if random.random() <= self.local_prob:
            # Find all local nodes with the same consistency.
            neighbors = [
                node for node in self.neighbors(consistency=self.consistency)
                if node.location == self.location
            ]

            # If we have local nodes, choose one of them
            if neighbors: return random.choice(neighbors)
            return random.choice(self.neighbors())

        # At this point return a wide area node
        neighbors = [
            node for node in self.neighbors(consistency=self.consistency)
            if node.location != self.location
        ]

        # If we have wide area nodes, choose one of them
        if neighbors: return random.choice(neighbors)
        return random.choice(self.neighbors())
