# cloudscope.replica.federated.sequential
# Implements sequential (strong) consistency in a federated environment.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jun 15 22:07:55 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: sequential.py [] benjamin@bengfort.com $

"""
Implements sequential (strong) consistency in a federated environment.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.replica.consensus import RaftReplica
from cloudscope.replica.eventual import Gossip
from cloudscope.replica.eventual import GossipResponse

##########################################################################
## Federated Sequential (Raft) Replica
##########################################################################

class FederatedRaftReplica(RaftReplica):

    def recv(self, event):
        """
        Pass Gossip messages through, all other methods to super.
        TODO: Organize better.
        """
        message = event.value
        rpc = message.value

        if isinstance(rpc, Gossip):
            # Pass directly to dispatcher
            return super(RaftReplica, self).recv(event)

        # Do the normal Raft thing
        return super(FederatedRaftReplica, self).recv(event)

    def on_gossip_rpc(self, message):
        """
        Handles the receipt of a gossip from another node. Expects multiple
        accesses (Write events) as entries. Goes through all and compares the
        versions, replying False only if there is an error or a conflict.

        TODO: Organize better, this is just a copy and paste from eventual.
        """
        entries = message.value.entries
        updates = []
        objects = set(entry.name for entry in entries)

        # Go through the entries from the RPC and update log
        for access in entries:
            current = self.log.get_latest_version(access.name)
            if current is None or access.version > current:
                self.write(access)

            elif access.version < current:
                updates.append(current.access)

            else:
                continue

        # Send back anything in local cache that wasn't received,
        # In this case, the latest version of every item in the log.
        for key, version in self.log.items():
            if key not in objects and version is not None:
                updates.append(version.access)

        # Success here just means whether or not we're responding with updates
        success = True if updates else False

        # Respond to the sender
        self.send(message.source, GossipResponse(updates, len(updates), success))
