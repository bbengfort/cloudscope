# cloudscope.replica.consensus.base
# The base class for consensus oriented replicas.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Apr 05 14:36:58 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: base.py [f37a55a] benjamin@bengfort.com $

"""
The base class for consensus oriented replicas.

This class essentially provides helper functions for replicas that do
consensus oriented protocols.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.replica import Replica


##########################################################################
## Base class for all Consensus Replicas
##########################################################################

class ConsensusReplica(Replica):

    ######################################################################
    ## Helper Methods
    ######################################################################

    def quorum(self):
        """
        Returns all nodes connected to this node who have the same consistency
        level (e.g. Strong for Raft), as well as self for a complete election.
        """
        # Filter only connections that are in same consistency group
        for node in self.neighbors(self.consistency):
            yield node

        # Don't forget to yield self!
        yield self
