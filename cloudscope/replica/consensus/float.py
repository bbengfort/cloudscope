# cloudscope.replica.consensus.float
# Implements strong consistency across a wide area using Raft + anti-entropy.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 06:57:45 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: float.py [] benjamin@bengfort.com $

"""
Implements strong consistency across a wide area using Raft + anti-entropy.
"""

##########################################################################
## Imports
##########################################################################

import random

from cloudscope.config import settings
from cloudscope.simulation.timer import Timer
from cloudscope.utils.decorators import memoized
from cloudscope.replica import Consistency, State
from cloudscope.replica.access import Read, Write
from cloudscope.exceptions import RaftRPCException, SimulationException

from .raft import RaftReplica
from .election import Election

from collections import namedtuple

##########################################################################
## Module Constants
##########################################################################

## Timers and timing
HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval
ELECTION_TIMEOUT   = settings.simulation.election_timeout
ANTI_ENTROPY_DELAY = settings.simulation.anti_entropy_delay

## RPC Message Definition
Gossip = namedtuple('Gossip', 'entries, length, term')
GossipResponse = namedtuple('GossipResponse', 'entries, length, success, term')

##########################################################################
## Raft Replica
##########################################################################

class FloatedRaftReplica(RaftReplica):

    def __init__(self, simulation, **kwargs):
        ## Initialize the replica
        super(FloatedRaftReplica, self).__init__(simulation, **kwargs)

        # Anti entropy settings
        self.ae_delay = kwargs.get('anti_entropy_delay', ANTI_ENTROPY_DELAY)
        self.ae_timer = None
        self.ae_cache = []

    @memoized
    def locations(self):
        """
        Returns all the locations in the network with Raft nodes.
        """
        return set([
            node.location for node in self.neighbors(self.consistency)
        ])

    def quorum(self):
        """
        Returns only nodes in the same location to do Raft consensus with.
        """

        # Filter only connections that are in the same consistency group
        for node in self.neighbors(self.consistency):
            if node.location == self.location:
                yield node

        # Don't forget to yield self!
        yield self

    def remotes(self, location=None):
        """
        Returns only nodes that are not in the same location to float writes
        to using anti-entropy. This method is only used by the leader.
        Can also specify a specific location to fetch the remotes for. Note
        that specifying your current location will not return nodes.
        """

        # Filter only connections that are in the same consistency group
        for node in self.neighbors(self.consistency):
            if node.location != self.location:
                if location is not None and node.location != location:
                    continue
                yield node

    def gossip(self):
        """
        Randomly select a neighbor and exchange information about the state
        of the latest entries in the log since the last anti-entropy delay.
        """

        # Gossip to one node at each location
        for location in self.locations:
            # Don't gossip to nodes in self!
            if location == self.location: continue

            # Select a random target to gossip to
            target = random.choice(list(self.remotes(location)))

            # Log the gossip that's happening
            self.sim.logger.debug(
                "{} gossiping {} entries to {}".format(
                    self, len(self.ae_cache), target
                )
            )

            entries = tuple([
                Write(version.name, self, version)
                for version in self.ae_cache
            ])

            # Send all the values in the cache.
            self.send(target, Gossip(entries, len(self.ae_cache), -1))

        # Empty the cache on gossip
        self.ae_cache = []

        # Reset the anti-entropy timer
        self.ae_timer = Timer(self.env, self.ae_delay, self.gossip)
        self.ae_timer.start()

    ######################################################################
    ## Event Handlers
    ######################################################################

    def on_state_change(self):
        """
        Does the same stuff as super, but also - if leader; starts the anti
        entropy interval to do gossiping.
        """
        super(FloatedRaftReplica, self).on_state_change()

        if self.state in (State.FOLLOWER, State.CANDIDATE):
            if hasattr(self, 'ae_timer') and self.ae_timer is not None:
                # Cancel the anti-entropy timer.
                self.ae_timer.stop()
                self.ae_timer = None
        elif self.state == State.LEADER:
            self.ae_timer = Timer(self.env, self.ae_delay, self.gossip)
            self.ae_timer.start()
        elif self.state == State.READY:
            # This happens on the call to super, just ignore for now.
            pass
        else:
            raise SimulationException(
                "Unknown Floating Raft State: {!r} set on {}".format(self.state, self)
            )

    def on_gossip_rpc(self, message):
        """
        Handles the receipt of a gossip from another node. Expects multiple
        accesses (Write events) as entries. Goes through all and compares the
        versions, replying False only if there is an error or a conflict.
        """
        entries = message.value.entries

        # Go through the entries from the RPC and write to local cluster.
        for access in entries:
            access.version.gossiped = True
            self.write(access)

        # Should we return with what's in our cache?
        # Respond to the sender
        self.send(message.source, GossipResponse([], 0, True, -1))

    def on_response_rpc(self, message):
        """
        Just receives the acknowledgment of the response.
        """
        pass

    def on_ae_response_rpc(self, msg):
        """
        Does the same stuff that the super handler does, but also caches
        commits to gossip about them later!
        """
        rpc = msg.value

        if self.state == State.LEADER:

            if rpc.success:
                self.nextIndex[msg.source]  = rpc.lastLogIndex + 1
                self.matchIndex[msg.source] = rpc.lastLogIndex

            else:
                # Decrement next index and retry append entries
                self.nextIndex[msg.source] -= 1
                self.send_append_entries(msg.source)

            # Decide if we can commit the entry
            for n in xrange(self.log.lastApplied, self.log.commitIndex, -1):
                commit = Election(self.matchIndex.keys())
                for k, v in self.matchIndex.iteritems():
                    commit.vote(k, v >= n)

                if commit.has_passed() and self.log[n][1] == self.currentTerm:
                    # Commit all versions from the last log entry to now.
                    for idx in xrange(self.log.commitIndex, n+1):
                        if self.log[idx][0] is None: continue

                        # Cache the version to anti-entropy!
                        version = self.log[idx][0]
                        if not hasattr(version, 'gossiped') or not version.gossiped:
                            self.ae_cache.append(version)

                        self.log[idx][0].update(self, commit=True)

                    # Set the commit index and break
                    self.log.commitIndex = n
                    break

        elif self.state == State.CANDIDATE:

            # Decide whether or not to step down.
            if rpc.term >= self.currentTerm:
                ## Become a follower
                self.state = State.FOLLOWER

                ## Log the failed election
                self.sim.logger.info(
                    "{} has stepped down as candidate".format(self)
                )

                return

        elif self.state == State.FOLLOWER:
            # Ignore AE messages if we are the follower.
            return

        else:
            raise RaftRPCException(
                "Append entries response in unknown state: '{}'".format(self.state)
            )
