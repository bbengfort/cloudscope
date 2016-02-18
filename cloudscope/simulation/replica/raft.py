# cloudscope.simulation.replica.raft
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

from .base import Replica, Consistency
from cloudscope.config import settings
from cloudscope.dynamo import Uniform
from cloudscope.simulation.timer import Timer
from cloudscope.simulation.replica.store import Version
from cloudscope.exceptions import RaftRPCException, SimulationException

from collections import defaultdict
from collections import namedtuple

##########################################################################
## Module Constants
##########################################################################

## Raft Replica State Enum
LEADER    = 0
CANDIDATE = 1
FOLLOWER  = 2

# Timers and timing
HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval
ELECTION_TIMEOUT   = settings.simulation.election_timeout

## RPC Messages
AppendEntries = namedtuple('AppendEntries', 'term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit')
RequestVote = namedtuple('RequestVote', 'term, candidateId, lastLogIndex, lastLogTerm')
Response = namedtuple('Response', 'term, success')
RemoteWrite = namedtuple('RemoteWrite', 'term')


##########################################################################
## Election Timer
##########################################################################

class ElectionTimer(Timer):
    """
    Specialized Timer for handling elections.
    """

    def __init__(self, replica, delay=ELECTION_TIMEOUT):
        super(ElectionTimer, self).__init__(
            replica.env, delay, replica.on_election_timeout
        )

    @property
    def delay(self):
        """
        Computes a random delay from the election timeout range.
        """
        return self._delay.get()

    @delay.setter
    def delay(self, delay):
        """
        Creates a uniform distribution based on a delay range.
        """
        self._delay = Uniform(*delay)

##########################################################################
## Raft Replica
##########################################################################

class RaftReplica(Replica):

    def __init__(self, simulation, **kwargs):
        ## Initialize the replica
        super(RaftReplica, self).__init__(simulation, **kwargs)

        ## Initialize Raft Specific settings
        self.state = FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.log = [(None, 0)]
        self.timeout   = ElectionTimer(self)
        self.heartbeat = Timer(self.env, HEARTBEAT_INTERVAL, self.on_heartbeat_timeout)

        # Volatile state
        self.commit_index = 0
        self.last_applied = 0

        # Leader state
        self.next_index   = None
        self.match_index  = None

    @property
    def n_majority(self):
        """
        Computes the number of votes required for a majority vote.
        """
        # Quorum is # of strong nodes connected, plus local node
        nodes = sum(1 for node in self.quorum)

        # Majority is integer division by 2 + 1.
        return (nodes / 2) + 1

    @property
    def state(self):
        """
        Manages the state of the node when being set.
        """
        return self._state

    @state.setter
    def state(self, state):
        """
        Setting the state decides how the Raft node will interact.
        """
        if state in (FOLLOWER, CANDIDATE):
            self.voted_for    = None
            self.next_index   = None
            self.match_index  = None
        elif state == CANDIDATE:
            pass
        elif state == LEADER:
            self.next_index   = {node: self.last_applied + 1 for node in self.quorum if node != self}
            self.match_index  = {node: 0 for node in self.quorum if node != self}
        else:
            raise SimulationException(
                "Unknown Raft State: {!r} set on {}".format(state, self)
            )

        self._state = state

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

    def on_heartbeat_timeout(self):
        """
        Callback for when a heartbeat timeout occurs, for AppendEntries RPC.
        """
        if not self.state == LEADER:
            return

        self.broadcast(
            AppendEntries(self.current_term, self.id, self.last_applied, self.log[self.last_applied][1], [], self.commit_index)
        )

    def on_election_timeout(self):
        """
        Callback for when an election timeout occurs, e.g. become candidate.
        """
        self.current_term += 1
        self.voted_for = self.id
        self.state = CANDIDATE
        self.votes = {self.id: True}

        self.broadcast(
            RequestVote(self.current_term, self.id, self.last_applied, self.log[self.last_applied][1])
        )

        self.sim.logger.info(
            "{} is now a leader candidate".format(self)
        )

    def on_request_vote(self, msg):
        """
        Callback for RequestVote RPC call.
        """
        rpc = msg.value

        if rpc.term < self.current_term:
            return self.send(
                msg.source, Response(self.current_term, False)
            )

        if self.voted_for is None or self.voted_for == rpc.candidateId:
            if self.log[-1][1] < rpc.lastLogTerm or (
                self.log[-1][1] == rpc.lastLogTerm and rpc.lastLogIndex >= (len(self.log) - 1)
            ):
                self.sim.logger.debug("{} stopping election timeout".format(self))
                self.timeout.stop()
                self.sim.logger.info(
                    "{} voting for {}".format(self, rpc.candidateId)
                )
                self.voted_for = rpc.candidateId
                self.send(
                    msg.source, Response(self.current_term, True)
                )

    def on_append_entries(self, msg):
        """
        Callback for the AppendEntries RPC call.
        """
        rpc = msg.value

        # Stop the election timeout
        self.timeout.stop()

        # Reply false if term < current term
        if rpc.term < self.current_term:
            return self.send(
                msg.source, Response(self.current_term, False)
            )

        # Reply false if log doesn't contain an entry at prevLogIndex whose
        # term matches previous log term.
        if len(self.log) <= rpc.prevLogIndex or self.log[rpc.prevLogIndex][1] != rpc.prevLogTerm:
            return self.send(
                msg.source, Response(self.current_term, False)
            )

        # At this point AppendEntries RPC is accepted
        if rpc.entries:
            if len(self.log) > rpc.prevLogIndex:
                # If existing entry conflicts with new one (same index, different terms)
                # Delete the existin entry and all that follow it.
                if self.log[rpc.prevLogIndex][1] != rpc.entries[0][1]:
                    self.log = self.log[:rpc.prevLogIndex]

            # Append any new entries not already in the log.
            for entry in rpc.entries:
                self.log.append(entry)

            # Set the current log index
            # TODO: create a log data structure that does this for us
            self.last_applied = len(self.log) - 1

        # If leaderCommit > commitIndex, update commit Index
        if rpc.leaderCommit > self.commit_index:
            self.commit_index = min(rpc.leaderCommit, self.last_applied)

    def on_rpc_response(self, msg):
        """
        Callback for AppendEntries and RequestVote RPC response.
        """
        rpc = msg.value

        if self.state == FOLLOWER:
            return

        if self.state == CANDIDATE:
            if self.current_term < rpc.term:
                self.current_term = rpc.term

            self.votes[msg.source.id] = rpc.success

            if sum(1 for v in self.votes.values() if v) >= self.n_majority:
                self.sim.logger.debug("{} stopping election timeout".format(self))
                self.timeout.stop()
                self.sim.logger.info(
                    "{} has become raft leader".format(self)
                )
                ## Now to deal with transforming into the leader!
                self.state = LEADER

        elif self.state == LEADER:

            if rpc.success:
                self.next_index[msg.source]  = self.last_applied + 1
                self.match_index[msg.source] = self.last_applied

            else:
                self.next_index[msg.source] -= 1
                nidx = self.next_index[msg.source]
                entries = self.log[nidx:]
                self.send(
                    msg.source, AppendEntries(self.current_term, self.id, self.last_applied, self.log[self.last_applied][1], entries, self.commit_index)
                )

            for n in xrange(self.last_applied, self.commit_index, -1):
                if sum(1 for v in self.match_index.values() if v >= n) >= self.n_majority:
                    if self.log[n][1] == self.current_term:
                        self.commit_index = n
                        break

        else:
            raise RaftRPCException(
                "Response in unknown state: '{}'".format(self.state)
            )


    def recv(self, event):
        """
        Passes messages to their appropriate message handlers.
        """
        message = event.value
        rpc = message.value

        # If RPC request or response contains term > current_term
        # Set current_term to term and conver to follower.
        if rpc.term > self.current_term:
            self.state = FOLLOWER
            self.current_term = rpc.term

        handler = {
            "RequestVote": self.on_request_vote,
            "Response": self.on_rpc_response,
            'AppendEntries': self.on_append_entries,
            "RemoteWrite": self.write,
        }[rpc.__class__.__name__]

        handler(message)

    def run(self):
        """
        Implements the Raft consensus protocol and elections.
        """
        while True:
            if self.state in {FOLLOWER, CANDIDATE}:
                yield self.timeout.start()

            elif self.state == LEADER:
                yield self.heartbeat.start()

            else:
                raise SimulationException(
                    "Unknown Raft State: {!r} on {}".format(self.state, self)
                )

    def write(self, message=None):
        """
        Forks the current version if it exists or creates a new version.
        Appends the version to the log and gets ready for AppendEntries.

        If this node is not the leader, then it simply forwards the write to
        the leader via a remote write call (e.g. sending a message with the
        write request, though this will have to be considered in more detail).
        """
        if not self.state == LEADER:
            leaders = [node for node in self.connections if node.state == LEADER]
            if len(leaders) > 1:
                raise SimulationException("MutipleLeaders?!")
            elif len(leaders) < 1:
                self.logging.info("no leader: dropped write at {}".format(self))
                return False
            else:
                # Forward the write to the leader
                return self.send(
                    leaders[0], RemoteWrite(self.current_term)
                )

        # Get the current version
        version = self.log[-1][0]

        # Write to the version
        version = Version(self) if version is None else version.fork(self)

        # Log the write
        self.sim.logger.info(
            "write version {} on {}".format(version, self)
        )

        # Write the new version to the local data store
        self.log.append((version, self.current_term))
        self.last_applied = len(self.log) - 1

        # Update the version to track visibility latency
        version.update(self)

        # Now do AppendEntries ...
        for follower, nidx in self.next_index.iteritems():
            if self.last_applied >= nidx:
                entries = self.log[nidx:]
                self.send(
                    follower, AppendEntries(self.current_term, self.id, self.last_applied, self.log[self.last_applied][1], entries, self.commit_index)
                )

        # Also interrupt the heartbeat since we just sent AppendEntries
        self.heartbeat.stop()
