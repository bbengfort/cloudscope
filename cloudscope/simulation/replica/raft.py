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
from cloudscope.exceptions import RaftRPCException

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
        self.timeout = ElectionTimer(self)

        # Volatile state
        self.commit_index = 0
        self.last_applied = 0

        # Leader state
        self.next_index   = None
        self.match_index  = None

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

        self.sim.logger.debug(
            "{} is now a leader candidate".format(self)
        )

    def on_request_vote(self, msg):
        """
        Callback for RequestVote RPC call.
        """
        self.state = 9
        rpc = msg.value

        if rpc.term < self.current_term:
            return self.send(
                msg.source, Response(self.current_term, False)
            )

        if self.voted_for is None or self.voted_for == rpc.candidateId:
            if self.log[-1][1] < rpc.lastLogTerm or (
                self.log[-1][1] == rpc.lastLogTerm and rpc.lastLogIndex >= (len(self.log) - 1)
            ):
                self.sim.logger.info("{} stopping election timeout".format(self))
                self.timeout.stop()
                self.sim.logger.debug(
                    "{} voting for {}".format(self, rpc.candidateId)
                )
                self.voted_for = rpc.candidateId
                self.send(
                    msg.source, Response(self.current_term, True)
                )

    def on_rpc_response(self, msg):
        """
        Callback for AppendEntries and RequestVote RPC response.
        """
        rpc = msg.value

        if self.state == CANDIDATE:
            if self.current_term < rpc.term:
                self.current_term = rpc.term

            self.votes[msg.source.id] = rpc.success
            # majority = len(filter(lambda r: r.consistency == Consistency.STRONG, self.connections))
            majority = 3
            print majority

            if sum(1 for v in self.votes.values() if v) >= majority:
                self.sim.logger.info("{} stopping election timeout".format(self))
                self.timeout.stop()
                self.sim.logger.info(
                    "{} has become raft leader".format(self)
                )
                ## Now to deal with transforming into the leader!
                self.state = LEADER

        elif self.state == LEADER:
            pass
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
        handler = {
            "RequestVote": self.on_request_vote,
            "Response": self.on_rpc_response,
        }[rpc.__class__.__name__]

        handler(message)

    def run(self):
        """
        Implements the Raft consensus protocol and elections.
        """
        while True:
            if self.state in {FOLLOWER, CANDIDATE}:
                self.sim.logger.info("{} starting election timeout".format(self))
                yield self.timeout.start()

            if self.state == LEADER:
                break
