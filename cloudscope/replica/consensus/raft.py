# cloudscope.replica.consensus.raft
# Implements strong consistency using Raft consensus.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 06:57:45 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: raft.py [] benjamin@bengfort.com $

"""
Implements strong consistency using Raft consensus.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.simulation.timer import Timer
from cloudscope.replica.store import Version
from cloudscope.replica import Replica, Consistency, State
from cloudscope.exceptions import RaftRPCException, SimulationException
from cloudscope.replica.store import MultiObjectWriteLog

from .election import ElectionTimer, Election

from collections import defaultdict
from collections import namedtuple

##########################################################################
## Module Constants
##########################################################################

## Response Type Enum
VOTE  = 0
ACK   = 1
WRITE = 2

# Timers and timing
HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval
ELECTION_TIMEOUT   = settings.simulation.election_timeout

## RPC Messages
AppendEntries = namedtuple('AppendEntries', 'term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit')
RequestVote   = namedtuple('RequestVote', 'term, candidateId, lastLogIndex, lastLogTerm')
Response      = namedtuple('Response', 'term, success, type')
RemoteWrite   = namedtuple('RemoteWrite', 'term, version')

##########################################################################
## Raft Replica
##########################################################################

class RaftReplica(Replica):

    def __init__(self, simulation, **kwargs):
        ## Initialize the replica
        super(RaftReplica, self).__init__(simulation, **kwargs)

        ## Initialize Raft Specific settings
        self.state       = State.FOLLOWER
        self.currentTerm = 0
        self.votedFor    = None
        self.log         = MultiObjectWriteLog()

        ## Timers for work
        eto = kwargs.get('election_timeout', ELECTION_TIMEOUT)
        hbt = kwargs.get('heartbeat_interval', HEARTBEAT_INTERVAL)

        self.timeout     = ElectionTimer.fromReplica(self, eto)
        self.heartbeat   = Timer(self.env, hbt, self.on_heartbeat_timeout)

        ## Leader state
        self.nextIndex   = None
        self.matchIndex  = None

    ######################################################################
    ## Properties
    ######################################################################

    @property
    def quorum(self):
        """
        Returns the nodes in the Raft quorum.
        """
        # Filter only connections that are strong
        is_strong = lambda r: r.consistency == Consistency.STRONG
        for node in filter(is_strong, self.connections):
            yield node

        # Don't forget to yield self!
        yield self

    @property
    def followers(self):
        """
        Returns all nodes in the Raft quorum, but self.
        """
        for node in self.quorum:
            if node != self:
                yield node

    ######################################################################
    ## Core Methods (Replica API)
    ######################################################################

    def recv(self, event):
        """
        Passes messages to their appropriate message handlers.
        """
        # Record the received message
        super(RaftReplica, self).recv(event)

        message = event.value
        rpc = message.value

        # If RPC request or response contains term > currentTerm
        # Set currentTerm to term and convert to follower.
        if rpc.term > self.currentTerm:
            self.state = State.FOLLOWER
            self.currentTerm = rpc.term

        handler = {
            "RequestVote": self.on_request_vote,
            "Response": self.on_rpc_response,
            'AppendEntries': self.on_append_entries,
            "RemoteWrite": self.on_remote_write,
        }[rpc.__class__.__name__]

        handler(message)

    def read(self, name=None):
        """
        Performs a read of the most recent committed version for the name
        passed in (or just a read for the most recent version, period).
        """
        name = name.name if isinstance(name, Version) else name
        vers = self.log.get_latest_commit(name)

        # Record the read latency as zero in raft (or we could do remote reads)
        self.sim.results.update(
            'read latency', (self.id, 0)
        )

        # Record the stale read and return the super.
        return super(RaftReplica, self).read(vers)

    def write(self, name=None):
        """
        Forks the current version if it exists or creates a new version.
        Appends the version to the log and gets ready for AppendEntries.

        If this node is not the leader, then it simply forwards the write to
        the leader via a remote write call (e.g. sending a message with the
        write request, though this will have to be considered in more detail).
        """
        # Figure out what is being written to the replica
        if isinstance(name, Version):
            # Then this is a remote write
            version = name
            name = version.name

            # Log the remote write
            self.sim.logger.debug(
                "remote write version {} on {}".format(version, self)
            )

        else:
            # This is a local write, fetch correct version from the store
            version = self.log.get_latest_version(name) if name is not None else self.log.lastVersion

            # Perform the fork for the write
            version = Version.new(name)(self) if version is None else version.fork(self)

            # Log the write
            self.sim.logger.info(
                "write version {} on {}".format(version, self)
            )

        # If not leader, remote write to the leader
        if not self.state == State.LEADER:
            leaders = [node for node in self.connections if node.state == State.LEADER]
            if len(leaders) > 1:
                raise SimulationException("MutipleLeaders?!")
            elif len(leaders) < 1:
                self.sim.logger.info("no leader: dropped write at {}".format(self))
                return False
            else:
                # Forward the write to the leader
                return self.send(
                    leaders[0], RemoteWrite(self.currentTerm, version)
                )

        # Write the new version to the local data store
        self.log.append(version, self.currentTerm)

        # Update the version to track visibility latency
        version.update(self)

        # Now do AppendEntries ...
        if not settings.simulation.aggregate_writes:
            self.send_append_entries()

            # Also interrupt the heartbeat since we just sent AppendEntries
            self.heartbeat.stop()

    def run(self):
        """
        Implements the Raft consensus protocol and elections.
        """
        while True:
            if self.state in {State.FOLLOWER, State.CANDIDATE}:
                yield self.timeout.start()

            elif self.state == State.LEADER:
                yield self.heartbeat.start()

            else:
                raise SimulationException(
                    "Unknown Raft State: {!r} on {}".format(self.state, self)
                )

    ######################################################################
    ## Helper Methods
    ######################################################################

    def send_append_entries(self, follower=None):
        """
        Helper function to send append entries to quorum or a specific node.

        Note: fails silently if follower is not in the followers list.
        """
        # Leader check
        if not self.state == State.LEADER:
            return

        # Go through follower list.
        for node, nidx in self.nextIndex.iteritems():
            # Filter based on the follower supplied.
            if follower is not None and node != follower:
                continue

            # Construct the entries, or empty for heartbeat
            entries = []
            if self.log.lastApplied >= nidx:
                entries = self.log[nidx:]

            # Compute the previous log index and term
            prevLogIndex = nidx - 1
            prevLogTerm  = self.log[prevLogIndex].term

            # Send the heartbeat message
            self.send(
                node, AppendEntries(
                    self.currentTerm, self.id, prevLogIndex,
                    prevLogTerm, entries, self.log.commitIndex
                )
            )

    ######################################################################
    ## Event Handlers
    ######################################################################

    def on_state_change(self):
        """
        When the state on a replica changes the internal state of the replica
        must also change, particularly the properties that define how the node
        interacts with RPC messages and client reads/writes.
        """
        if self.state in (State.FOLLOWER, State.CANDIDATE):
            self.votedFor    = None
            self.nextIndex   = None
            self.matchIndex  = None
        elif self.state == State.CANDIDATE:
            pass
        elif self.state == State.LEADER:
            self.nextIndex   = {node: self.log.lastApplied + 1 for node in self.followers}
            self.matchIndex  = {node: 0 for node in self.followers}
        else:
            raise SimulationException(
                "Unknown Raft State: {!r} set on {}".format(state, self)
            )

    def on_heartbeat_timeout(self):
        """
        Callback for when a heartbeat timeout occurs, for AppendEntries RPC.
        """
        if not self.state == State.LEADER:
            return

        # Send heartbeat or aggregated writes
        self.send_append_entries()

    def on_election_timeout(self):
        """
        Callback for when an election timeout occurs, e.g. become candidate.
        """
        # Set state to candidate
        self.state = State.CANDIDATE

        # Create Election and vote for self
        self.currentTerm += 1
        self.votes = Election([node.id for node in self.quorum])
        self.votes.vote(self.id)
        self.votedFor = self.id

        # Inform the rest of the quorum you'd like their vote.
        rpc = RequestVote(
            self.currentTerm, self.id, self.log.lastApplied, self.log.lastTerm
        )

        for follower in self.followers:
            self.send(
                follower, rpc
            )

        # Log the newly formed candidacy
        self.sim.logger.info(
            "{} is now a leader candidate".format(self)
        )

    def on_request_vote(self, msg):
        """
        Callback for RequestVote RPC call.
        """
        rpc = msg.value

        if rpc.term >= self.currentTerm:
            if self.votedFor is None or self.votedFor == rpc.candidateId:
                if self.log.as_up_to_date(rpc.lastLogTerm, rpc.lastLogIndex):

                    self.sim.logger.info(
                        "{} voting for {}".format(self, rpc.candidateId)
                    )

                    self.timeout.stop()
                    self.votedFor = rpc.candidateId
                    return self.send(
                        msg.source, Response(self.currentTerm, True, VOTE)
                    )

        return self.send(
            msg.source, Response(self.currentTerm, False, VOTE)
        )

    def on_append_entries(self, msg):
        """
        Callback for the AppendEntries RPC call.
        """
        rpc = msg.value

        # Stop the election timeout
        self.timeout.stop()

        # Reply false if term < current term
        if rpc.term < self.currentTerm:
            self.sim.logger.info("{} doesn't accept write on term {}".format(self, self.currentTerm))
            return self.send(
                msg.source, Response(self.currentTerm, False, ACK)
            )

        # Reply false if log doesn't contain an entry at prevLogIndex whose
        # term matches previous log term.
        if self.log.lastApplied < rpc.prevLogIndex or self.log[rpc.prevLogIndex][1] != rpc.prevLogTerm:
            if self.log.lastApplied < rpc.prevLogIndex:
                self.sim.logger.info(
                    "{} doesn't accept write on index {} where last applied is {}".format(
                        self, rpc.prevLogIndex, self.log.lastApplied
                    )
                )
            else:
                self.sim.logger.info(
                    "{} doesn't accept write for term mismatch {} vs {}".format(
                        self, rpc.prevLogTerm, self.log[rpc.prevLogIndex][1]
                    )
                )

            return self.send(
                msg.source, Response(self.currentTerm, False, ACK)
            )

        # At this point AppendEntries RPC is accepted
        if rpc.entries:
            if self.log.lastApplied >= rpc.prevLogIndex:
                # If existing entry conflicts with new one (same index, different terms)
                # Delete the existing entry and all that follow it.
                if self.log[rpc.prevLogIndex][1] != rpc.prevLogTerm:
                    self.log.remove(rpc.prevLogTerm)

            # Append any new entries not already in the log.
            for entry in rpc.entries:
                # Add the entry/term to the log
                self.log.append(*entry)
                self.sim.logger.debug(
                    "appending {} to {} on {}".format(entry[0], entry[1], self)
                )

                # Update the versions to compute visibilities
                entry[0].update(self)

            # Log the last write from the append entries.
            self.sim.logger.debug(
                "{} writes {} at idx {} (term {}, commit {})".format(
                self, self.log.lastVersion, self.log.lastApplied, self.log.lastTerm, self.log.commitIndex
            ))

        # If leaderCommit > commitIndex, update commit Index
        if rpc.leaderCommit > self.log.commitIndex:
            self.log.commitIndex = min(rpc.leaderCommit, self.log.lastApplied)

        # Return success response.
        return self.send(msg.source, Response(self.currentTerm, True, ACK))

    def on_rpc_response(self, msg):
        """
        Callback for AppendEntries and RequestVote RPC response.
        """
        rpc = msg.value

        if self.state == State.FOLLOWER:
            return

        if self.state == State.CANDIDATE:

            # If it's append entries, decide whether or not to step down.
            if rpc.type == ACK and rpc.term >= self.currentTerm:
                ## Become a follower
                self.state = State.FOLLOWER

                ## Log the failed election
                self.sim.logger.info(
                    "{} has stepped down as candidate".format(self)
                )

                return

            if rpc.type == VOTE:
                self.votes.vote(msg.source.id, rpc.success)
                if self.votes.has_passed():
                    ## Become the leader
                    self.state = State.LEADER
                    self.timeout.stop()

                    ## Log the new leader
                    self.sim.logger.info(
                        "{} has become raft leader".format(self)
                    )

                return

        elif self.state == State.LEADER:

            # Ignore votes after becoming leader
            if rpc.type == VOTE:
                return

            if rpc.success:
                self.nextIndex[msg.source]  = self.log.lastApplied + 1
                self.matchIndex[msg.source] = self.log.lastApplied

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
                        self.log[idx][0].update(self, commit=True)

                    # Set the commit index and break
                    self.log.commitIndex = n
                    break

        else:
            raise RaftRPCException(
                "Response in unknown state: '{}'".format(self.state)
            )

    def on_remote_write(self, msg):
        """
        Unpacks the version from the remote write and initiates a local write.
        """
        rpc = msg.value
        self.write(rpc.version)
