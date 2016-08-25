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
from cloudscope.replica.consensus.raft import WriteResponse
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

        # Go through the entries from the RPC and update log
        for access in entries:
            current = self.log.get_latest_version(access.name)

            # If the access is greater than our current version, write it!
            if current is None or access.version > current:
                self.write(access)

            # Is the the remote behind us? If so, send the latest version!
            elif access.version < current:
                updates.append(current.access)

            else:
                # Presumably the version are equal, so do nothing.
                continue

        # Success here just means whether or not we're responding with updates
        success = True if updates else False

        # Respond to the sender with the latest versions from our log
        self.send(message.source, GossipResponse(updates, len(updates), success))

    def on_remote_write_rpc(self, message):
        """
        Reject forked writes if they come in.
        """
        access = message.value.version

        # Check to make sure the write isn't forked - if it is, then reject.
        # TODO: Move to the write not just on remote write! 
        if access.version.parent and access.version.parent.is_forked():
            access.drop()
            success = False

            # Count the number of "unforked" writes
            # TODO: THIS IS A COMPLETE HACK!
            # TODO: GET RID OF THIS!
            self.sim.results.update(
                'unforked writes', (access.version.parent.writer.id, self.env.now)
            )

        else:
            self.write(access)
            success = True

        # Send the write response
        self.send(message.source, WriteResponse(self.currentTerm, success, access))
