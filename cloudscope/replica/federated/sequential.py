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
    """
    Implements Raft for sequential consistency while also allowing interaction
    with eventual consistency replicas.
    """

    ######################################################################
    ## Core Methods (Replica API)
    ######################################################################

    def recv(self, event):
        """
        Pass Gossip messages through, all other methods to super.
        """
        message = event.value
        rpc = message.value

        if isinstance(rpc, Gossip):
            # Pass directly to dispatcher
            return super(RaftReplica, self).recv(event)

        # Do the normal Raft thing which checks the term.
        return super(FederatedRaftReplica, self).recv(event)

    ######################################################################
    ## Message Event Handlers
    ######################################################################

    def on_gossip_rpc(self, message):
        """
        Handles the receipt of a gossip from another node. Expects multiple
        accesses (Write events) as entries. Goes through all and compares the
        versions, replying False only if there is an error or a conflict.
        """
        entries = message.value.entries
        updates = []

        # Go through the entries from the RPC and update log
        for access in entries:

            # Read via policy will ensure we use a locally cached version or
            # if we're enforcing commits, the latest committed version.
            current = self.read_via_policy(access.name)

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

    def append_via_policy(self, access, complete=False):
        """
        This method is the gatekeeper for the log and can implement policies
        like "don't admit forks". It must drop the access if it doesn't meet
        the policy, and complete it if specified.

        The Federated version implements two policies:

            - The version must be later than the leader's current version.
            - The version's parent must not be forked.

        If neither of these policies are met, the access is dropped.

        NOTE: This is a leader-only method (followers have entries appended
        to their logs via AppendEntries) and will raise an exception if the
        node is not the leader.
        """

        # Check to make sure the write isn't forked - if it is, then drop.
        if access.version.parent and access.version.parent.is_forked():
            access.drop()

            # Fork detection only counts undropped accesses, so by dropping
            # this access we have "unforked" the write. Track this so we can
            # analyze how Raft impacts the federated system.
            self.sim.results.update(
                'unforked writes', (access.version.parent.writer.id, self.env.now)
            )

            # Indicate no append to the log occurred
            return False

        # Check to make sure that the access is later than our latest version.
        current = self.read_via_policy(access.name)
        if current is not None and access.version  <= current:
            access.drop()

            self.sim.results.update(
                'unordered writes', (access.version.writer.id, self.env.now)
            )

            # Indicate no append to the log occurred
            return False

        # Calling super ensures that the access is appended to the log.
        super(FederatedRaftReplica, self).append_via_policy(access, complete)
