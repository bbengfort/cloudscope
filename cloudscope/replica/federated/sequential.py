# cloudscope.replica.federated.sequential
# Implements sequential (strong) consistency in a federated environment.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jun 15 22:07:55 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: sequential.py [4a2f715] benjamin@bengfort.com $

"""
Implements sequential (strong) consistency in a federated environment.
"""

##########################################################################
## Imports
##########################################################################

import random

from cloudscope.config import settings
from cloudscope.replica.consensus import RaftReplica
from cloudscope.replica.consensus.raft import WriteResponse
from cloudscope.replica.eventual import Gossip, Rumor
from cloudscope.replica.eventual import GossipResponse, RumorResponse
from cloudscope.simulation.timer import Interval
from cloudscope.replica import Consistency


##########################################################################
## Module Constants
##########################################################################

## Fetch simulation settings from defaults
AE_DELAY    = settings.simulation.anti_entropy_delay
NEIGHBORS   = settings.simulation.num_neighbors


##########################################################################
## Federated Sequential (Raft) Replica
##########################################################################

class FederatedRaftReplica(RaftReplica):
    """
    Implements Raft for sequential consistency while also allowing interaction
    with eventual consistency replicas.
    """

    def __init__(self, simulation, **kwargs):
        # Eventually consistent settings
        self.ae_delay     = kwargs.get('anti_entropy_delay', AE_DELAY)
        self.n_neighbors  = kwargs.get('num_neighbors', NEIGHBORS)

        self.anti_entropy = Interval(simulation.env, self.ae_delay, self.gossip)

        # Must follow the anti-entropy interval setup.
        super(FederatedRaftReplica, self).__init__(simulation, **kwargs)

    ######################################################################
    ## Core Methods (Replica API)
    ######################################################################

    def recv(self, event):
        """
        Pass Gossip messages through, all other methods to super.
        """
        message = event.value
        rpc = message.value

        if isinstance(rpc, (Gossip, GossipResponse)):
            # Pass directly to dispatcher
            return super(RaftReplica, self).recv(event)

        # Do the normal Raft thing which checks the term.
        return super(FederatedRaftReplica, self).recv(event)

    def run(self):
        """
        Implements the Raft consensus protocol and elections and also starts
        an anti-entropy interval to gossip with other nodes.
        """
        # Start the anti entropy interval.
        self.anti_entropy.start()
        return super(FederatedRaftReplica, self).run()

    ######################################################################
    ## Helper Methods
    ######################################################################

    def gossip(self):
        """
        Pairwise gossip protocol by randomly selecting a neighbor and
        exchanging information about the state of the latest objects in the
        cache since the last anti-entropy delay.
        """
        # Perform pairwise anti-entropy sessions with n_neighbors
        for target in self.get_anti_entropy_neighbors():
            # Send the latest version of ALL objects.
            entries = [
                self.read_via_policy(name).access
                for name in self.log.namespace
            ]
            gossip  = Gossip(tuple(entries), len(entries))
            self.send(target, gossip)

    def select_anti_entropy_neighbor(self):
        """
        Implements the anti-entropy neighbor selection policy. By default this
        is simply uniform random selection of all the eventual neighbors.
        """
        # Find all local nodes with the same consistency.
        neighbors = self.neighbors(
            consistency=[Consistency.EVENTUAL, Consistency.STENTOR],
            location=self.location
        )

        # If we have local nodes, choose one of them
        if neighbors: return random.choice(neighbors)

    def get_anti_entropy_neighbors(self):
        """
        Selects the neighbors to perform anti-entropy with.
        """
        for _ in xrange(self.n_neighbors):
            neighbor = self.select_anti_entropy_neighbor()
            if neighbor: yield neighbor

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

    def update_forte_children(self, current, remote):
        """
        This unfortunately named method is a recursive function that updates
        all the children of the remote version with the new forte number and
        returns the newly correct current version.

        The idea here is that if the current version has a lower forte number
        then we should update the children of the remote (higher forte) in
        order to make sure that the latest branch is current.

        This method provides backpressure from Raft to Eventual.
        """

        def update_forte(forte, version, current):
            """
            Recursive update the forte number for a particular version.
            """
            # Update all the version's children with its forte number.
            for child in version.children:
                # Only update children that are in the current log.
                if child in self.log:
                    # Update child forte to parent and detect current
                    child.forte = forte
                    if child > current: current = child

                # Recurse on grandchildren
                current = update_forte(forte, child, current)

            # Return the maximal version (using forte numbers) discovered.
            return current

        # This function only needs be called if we're in federated versioning.
        if settings.simulation.versioning != "federated":
            return current

        # If the current is greater than the remote, return it.
        if current is None or current >= remote: return current

        # Check the forte number on the remote and update the children.
        if remote.forte > current.forte:
            strong = update_forte(remote.forte, remote, current)
            if strong > current:
                # Put the strong version into the cache
                self.cache[strong.name] = strong
                return strong

        # Last resort, return the current version.
        return current

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
            current = self.update_forte_children(current, access.version)

            # Is the access forked? If so, reject the update (drop).
            # For now we will simply send the current version as an update.
            # NOTE: the remote node will likely ignore the later version.
            if access.version.parent and access.version.parent.is_forked():
                access.drop()

                # Fork detection only counts undropped accesses, so by dropping
                # this access we have "unforked" the write. Track this so we can
                # analyze how Raft impacts the federated system.
                self.sim.results.update(
                    'unforked writes', (access.version.parent.writer.id, self.env.now)
                )

                # Send back the current, unforked version if we have one.
                if current: updates.append(current.access)

            # If the access is greater than our current version, write it!
            elif current is None or access.version > current:
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

    def on_gossip_response_rpc(self, message):
        """
        Handles the response to pairwise gossiping, updating entries from the
        responder's cache to the local log and latest version cache.
        """
        entries = message.value.entries

        for access in entries:
            current = self.read_via_policy(access.name)
            current = self.update_forte_children(current, access.version)

            # This is a new version or a later version than our current.
            if current is None or access.version > current:
                self.write(access)

    def on_dropped_message(self, target, value):
        """
        Called when there is a network error and a message that is being sent
        is dropped - for Federated Raft, we must do both the check for the
        unavailable leader and if anti-entropy has failed.
        """

        # Log the dropped message
        super(FederatedRaftReplica, self).on_dropped_message(target, value)

        # Drop any writes that can't be sent to the leader.
        if isinstance(value, (Gossip, Rumor)):
            self.sim.logger.info(
                "anti-entropy between {} and {} failed".format(self, target), color="LIGHT_RED"
            )
