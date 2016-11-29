# cloudscope.replica.eventual
# Implements the anti-entropy and eventual consistency policies on a replica.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Feb 17 06:36:33 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: eventual.py [c2eb7ed] benjamin@bengfort.com $

"""
Implements the anti-entropy and eventual consistency policies on a replica.
[Eventual consistency][ec] requires two things:

1. method of exchanging data (anti-entropy)
2. method of reconcilliation

Anti Entropy
============

Writes are gossiped to and from causal/eventual devices for [anti-entropy][gossip]
    - pushed via [rumor-mongering][gp]
    - pulled via periodic gossip
    - random targets in both cases

Writes are always pushed in in-order.
    - first find out what target has (remote read)
    - then push everything the source has at the target (remote write).
    - only new versions are pushed (some devices might not get old versions).

Reconcilliation
===============

Last writer wins. Reconcillation is scheduled via asynchronous repair, e.g.
not part of a read/write operation, and is therefore part of the anti-entropy
mechanism rather than any remote reads/writes.

[ec]: https://en.wikipedia.org/wiki/Eventual_consistency
[gossip]: https://en.wikipedia.org/wiki/Gossip_protocol
[gp]: http://www.inf.u-szeged.hu/~jelasity/ddm/gossip.pdf
"""

##########################################################################
## Imports
##########################################################################

import random

from .base import Replica
from .store import namespace
from .store import MultiObjectWriteLog

from cloudscope.config import settings
from cloudscope.simulation.timer import Timer
from cloudscope.exceptions import AccessError

from collections import defaultdict
from collections import namedtuple

##########################################################################
## Module Constants
##########################################################################

## Fetch simulation settings from defaults
AE_DELAY    = settings.simulation.anti_entropy_delay
NEIGHBORS   = settings.simulation.num_neighbors

# Deprecated
DO_GOSSIP   = settings.simulation.do_gossip
DO_RUMORING = settings.simulation.do_rumoring

## RPC Message Definition
Gossip   = namedtuple('Gossip', 'entries, length')
GossipResponse = namedtuple('GossipResponse', 'entries, length, success')
Rumor    = namedtuple('Rumor', 'access')
RumorResponse  = namedtuple('RumorResponse', 'access, success')

##########################################################################
## Eventual Replica
##########################################################################

class EventualReplica(Replica):

    def __init__(self, simulation, **kwargs):
        super(EventualReplica, self).__init__(simulation, **kwargs)

        # Eventually consistent settings
        self.ae_delay    = kwargs.get('anti_entropy_delay', AE_DELAY)
        self.n_neighbors = kwargs.get('num_neighbors', NEIGHBORS)

        # Deprecated
        self.do_gossip   = kwargs.get('do_gossip', DO_GOSSIP)
        self.do_rumoring = kwargs.get('do_rumoring', DO_RUMORING)

        self.log         = MultiObjectWriteLog() # the write log of the replica
        self.timeout     = None                  # anti entropy timer

    ######################################################################
    ## Properties
    ######################################################################

    ######################################################################
    ## Core Methods (Replica API)
    ######################################################################

    def read(self, name, **kwargs):
        """
        Eventually consistent replicas simply return the latest version for
        the name that they have in their store. This easily could be stale or
        forked depending on writes elsewhere in the cluster.
        """
        # Create the read event using super.
        access  = super(EventualReplica, self).read(name, **kwargs)

        # Record the number of attempts for the access
        if access.is_local_to(self): access.attempts += 1

        # Fetch the latest version from the log
        version = self.log.get_latest_version(access.name)

        # If version is None then we haven't read anything; bail!
        if version is None: return access.drop(empty=True)

        # Eventual nodes read locally and immediately, so complete the read.
        access.update(version, completed=True)

        # Log the access from this particular replica.
        access.log(self)

        return access

    def write(self, name, **kwargs):
        """
        Performs a write to the object with the given name by first creating
        the access event using super. Note that other access events can be
        passed into the write method in the case of remote writes.

        The access will define if the write is local or not.
        If local: write to the latest local version and complete.
        If remote: append write to log if latest version of object else error.

        After local vs. remote do the following:

        1. append the write to the log as (version, id)
        2. cache the latest access for gossip or rumoring
        3. update the version for visibility latency
        4. call the rumor handler

        Note this method can raise an error if not writing the latest version.
        """
        # Create the write event using super.
        access  = super(EventualReplica, self).write(name, **kwargs)

        # Determine if the write is local or remote
        if access.is_local_to(self):
            # Record the number of attempts for the access
            access.attempts += 1

            # Fetch the latest version from the log
            latest  = self.log.get_latest_version(access.name)

            # Perform the write
            if latest is None:
                version = namespace(access.name)(self)
            else:
                version = latest.nextv(self)

            # Update the access with the latest version and complete
            access.update(version, completed=True)

        else:

            # If there is no version, raise an exception
            if access.version is None:
                raise AccessError(
                    "Attempting a remote write on {} without a version!".format(self)
                )

            # Save the version variable for use below
            version = access.version
            current = self.log.get_latest_version(access.name)

            # Ensure that the version is the latest.
            if current is not None and version <= current:
                raise AccessError(
                    "Attempting unordered write of {} after write of {}".format(version, current)
                )

        # At this point we've dealt with local vs. remote
        # Append the latest version to the local data store
        self.log.append(version, 0)

        # Handle the access according to eventual rules
        version.update(self) # Update the version to track visibility latency
        access.log(self)     # Log the access from this particular replica.
        self.rumor(access)   # Rumor the access on demand

        # Return the access for subclass access.
        return access

    def run(self):
        """
        The run method basically implements an anti-entropy timer.
        """
        while True:
            yield self.get_anti_entropy_timeout()

    ######################################################################
    ## Helper Methods
    ######################################################################

    def gossip(self):
        """
        Pairwise gossip protocol by randomly selecting a neighbor and
        exchanging information about the state of the latest objects in the
        cache since the last anti-entropy delay.

        TODO: how to gossip to strong consistency nodes?
        """
        # If gossiping is not allowed, forget about it.
        if not self.do_gossip:
            return

        # Perform pairwise anti-entropy sessions with n_neighbors
        for target in self.get_anti_entropy_neighbors():
            # Send the latest version of ALL objects.
            entries = [
                self.log.get_latest_version(name).access
                for name in self.log.namespace
            ]
            gossip  = Gossip(tuple(entries), len(entries))
            self.send(target, gossip)

    def rumor(self, access):
        """
        Performs on access rumor mongering
        """
        # if rumoring is not allowed, forget about it.
        if not self.do_rumoring:
            return

        # Send the access to n other neighbors (excluding the origin)
        for target in self.get_anti_entropy_neighbors():
            rumor = Rumor(access)
            self.send(target, rumor)

    def get_anti_entropy_timeout(self):
        """
        Creates the anti-entropy timeout.
        In the future this could be random timeout not fixed.
        """
        self.timeout = Timer(self.env, self.ae_delay, self.gossip)
        return self.timeout.start()

    def select_anti_entropy_neighbor(self):
        """
        Implements the anti-entropy neighbor selection policy. By default this
        is simply uniform random selection of all the eventual neighbors.
        """
        return random.choice(self.neighbors(self.consistency))

    def get_anti_entropy_neighbors(self):
        """
        Selects the neighbors to perform anti-entropy with.
        """
        for _ in xrange(self.n_neighbors):
            yield self.select_anti_entropy_neighbor()

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
                # Put the strong version at the end of the log and return it
                # as the new current version (or latest for this object)
                if strong in self.log:
                    self.log.remove(strong)
                    self.log.append(strong, strong.forte)
                    return strong
                else:
                    # This really shouldn't happen?!
                    self.sim.logger.warning(
                        "Attempting to move {} to end when not in log!"
                    )

        # Last resort, return the current version.
        return current

    ######################################################################
    ## Event Handlers
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
            # Get the latest version from the log then update with forte
            current = self.log.get_latest_version(access.name)
            current = self.update_forte_children(current, access.version)

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

    def on_gossip_response_rpc(self, message):
        """
        Handles the response to pairwise gossiping, updating entries from the
        responder's cache to the local log and latest version cache.
        """
        entries = message.value.entries

        for access in entries:
            current = self.log.get_latest_version(access.name)
            current = self.update_forte_children(current, access.version)

            # This is a new version or a later version than our current.
            if current is None or access.version > current:
                self.write(access)

    def on_rumor_rpc(self, message):
        """
        Handles the rumor message from the originator of the rumor.
        """
        access  = message.value.access
        current = self.log.get_latest_version(access.name)
        current = self.update_forte_children(current, access.version)

        # Is the rumored version later than our current?
        if current is None or access.version > current:
            # Write the access which will rumor it out again
            self.write(access)

            # Respond True to the origin of the rumor
            response = RumorResponse(None, True)

        elif access.version < current:
            # Respond False to the origin with the later version
            response = RumorResponse(current.access, False)

        else:
            # Simply acknowledge receipt
            response = RumorResponse(None, True)

        # Send the response back to the source
        self.send(message.source, response)

    def on_rumor_response_rpc(self, message):
        """
        Handles the rumor acknowledgment
        """
        response = message.value
        if not response.success:
            # This means that a later value has come in!
            current = self.log.get_latest_version(response.access.name)
            current = self.update_forte_children(current, access.version)

            # If their response is later than our version, write it.
            if current is None or response.access.version > current:
                self.write(response.access)

    def on_dropped_message(self, target, value):
        """
        Called when there is a network error and a message that is being sent
        is dropped - for Eventual, we simply log the fact that anti-entropy
        could not occur, but we don't do much else.
        """

        # Log the dropped message
        super(EventualReplica, self).on_dropped_message(target, value)

        # Drop any writes that can't be sent to the leader.
        if isinstance(value, (Gossip, Rumor)):
            self.sim.logger.info(
                "anti-entropy between {} and {} failed".format(self, target), color="LIGHT_RED"
            )
