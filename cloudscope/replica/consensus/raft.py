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
from cloudscope.replica import Consistency, State
from cloudscope.exceptions import RaftRPCException, SimulationException
from cloudscope.replica.store import MultiObjectWriteLog
from cloudscope.utils.enums import Enum

from .base import ConsensusReplica
from .election import ElectionTimer, Election

from collections import defaultdict
from collections import namedtuple

##########################################################################
## Module Constants
##########################################################################

## Response Type Enum
RType = Enum("RType", "VOTE ACK")

## Timers and timing
HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval
ELECTION_TIMEOUT   = settings.simulation.election_timeout

## RPC Messages
AppendEntries = namedtuple('AppendEntries', 'term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit')
RequestVote   = namedtuple('RequestVote', 'term, candidateId, lastLogIndex, lastLogTerm')
Response      = namedtuple('Response', 'term, success, type')
RemoteWrite   = namedtuple('RemoteWrite', 'term, version')
WriteResponse = namedtuple('WriteResponse', 'term, success, access')

##########################################################################
## Raft Replica
##########################################################################

class RaftReplica(ConsensusReplica):

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
    ## Core Methods (Replica API)
    ######################################################################

    def recv(self, event):
        """
        Before dispatching the message to an RPC specific handler, there are
        some message-wide checks that need to occur. In this case the term
        must be inspected and if the replica is behind, become follower.
        """
        message = event.value
        rpc = message.value

        # If RPC request or response contains term > currentTerm
        # Set currentTerm to term and convert to follower.
        if rpc.term > self.currentTerm:
            self.state = State.FOLLOWER
            self.currentTerm = rpc.term

        # Record the received message and dispatch to event handler
        return super(RaftReplica, self).recv(event)

    def read(self, name, **kwargs):
        """
        Raft nodes perform a local read of the most recent commited version
        for the name passed in. Because the committed version could be stale
        (a new version is still waiting for 2 phase commit) a fork is possible
        but the Raft group will maintain full linearizability.
        """
        # Create the read event using super.
        access = super(RaftReplica, self).read(name, **kwargs)

        # Record the number of attempts for the access
        if access.is_local_to(self): access.attempts += 1

        # Fetch the most recent commit from the log.
        # This is the key difference between eventual if you're looking for it.
        version = self.log.get_latest_commit(access.name)

        # If the version is None, that we haven't read anything!
        if version is None: return

        # Because this is a local read committed, complete the read.
        access.update(version, completed=True)

        # Log the access from this particular replica.
        access.log(self)

        return access

    def write(self, name, **kwargs):
        """
        The write can be initiated on any replica server, including followers.
        Step one is to create the access event using super, which will give us
        the ability to detect local vs. remote writes.

        If the write is local:
        - create a new version from the latest write.
        - if follower: send a RemoteWrite with new version to the leader (write latency)
        - if leader: append to log and complete (no leader latency)

        If the write is remote:
        - if follower: log warning and forward to leader
        - if remote: append to log but do not complete (complete at local)

        Check the committed vs. latest new versions.

        After local vs. remote do the following:

        1. update the version for visibility latency
        2. if leader send append entries
        """
        access = super(RaftReplica, self).write(name, **kwargs)

        # Determine if the write is local or remote
        if access.is_local_to(self):
            # Record the number of attempts for the access
            access.attempts += 1

            # Fetch the latest version from the log
            latest = self.log.get_latest_version(access.name)

            # Perform the write
            if latest is None:
                version = Version.new(access.name)(self)
            else:
                version = latest.nextv(self)

            # Update the access with the latest version
            access.update(version)

            # Log the access from this particular replica.
            access.log(self)

            if self.state == State.LEADER:
                # Append to log and complete if leader and local
                self.log.append(version, self.currentTerm)
                access.complete()

            else:
                return self.send_remote_write(access)

        else:
            # Log the access from this particular replica.
            access.log(self)

            # If there is no version, raise an exception
            if access.version is None:
                raise AccessError(
                    "Attempting a remote write on {} without a version!".format(self)
                )

            # Save the version variable for use below.
            version = access.version

            if self.state == State.LEADER:
                # Append to log but do not complete since its remote
                self.log.append(version, self.currentTerm)

            else:
                # Why in the world did a remote write happen here?
                self.sim.logger.info(
                    "remote write on follower node: {}".format(self)
                )

                return self.send_remote_write(access)

        # At this point we've dealt with local vs. remote, we should be the leader
        assert self.state == State.LEADER

        # Update the version to track visibility latency
        version.update(self)

        # Now do AppendEntries
        # Also interrupt the heartbeat since we just sent AppendEntries
        if not settings.simulation.aggregate_writes:
            self.send_append_entries()
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

        Note: fails silently if follower is not in the neighbors list.
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

    def send_remote_write(self, access):
        """
        Helper function to send a remote write from a follower to leader.
        """
        # Find the leader to perform the remote write.
        leader = self.get_leader_node()

        # If not leader, then drop the write
        if not leader:
            self.sim.logger.info(
                "no leader: dropped write at {}".format(self)
            )
            return

        # Send the remote write to the leader
        self.send(
            leader, RemoteWrite(self.currentTerm, access)
        )

    def get_leader_node(self):
        """
        Searches for the leader amongst the neighbors. Raises an exception if
        there are multiple leaders, which is an extreme edge case.
        """
        leaders = [
            node for node in self.connections if node.state == State.LEADER
        ]

        if len(leaders) > 1:
            raise SimulationException("MutipleLeaders?!")
        elif len(leaders) < 1:
            return None
        else:
            return leaders[0]

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
            self.nextIndex   = {node: self.log.lastApplied + 1 for node in self.neighbors()}
            self.matchIndex  = {node: 0 for node in self.neighbors()}
        elif self.state == State.READY:
            pass
        else:
            raise SimulationException(
                "Unknown Raft State: {!r} set on {}".format(self.state, self)
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
        self.votes = Election([node.id for node in self.quorum()])
        self.votes.vote(self.id)
        self.votedFor = self.id

        # Inform the rest of the quorum you'd like their vote.
        rpc = RequestVote(
            self.currentTerm, self.id, self.log.lastApplied, self.log.lastTerm
        )

        for follower in self.neighbors():
            self.send(
                follower, rpc
            )

        # Log the newly formed candidacy
        self.sim.logger.info(
            "{} is now a leader candidate".format(self)
        )

    def on_request_vote_rpc(self, msg):
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
                        msg.source, Response(self.currentTerm, True, RType.VOTE)
                    )

        return self.send(
            msg.source, Response(self.currentTerm, False, RType.VOTE)
        )

    def on_append_entries_rpc(self, msg):
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
                msg.source, Response(self.currentTerm, False, RType.ACK)
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
                msg.source, Response(self.currentTerm, False, RType.ACK)
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
        return self.send(msg.source, Response(self.currentTerm, True, RType.ACK))

    def on_response_rpc(self, msg):
        """
        Callback for AppendEntries and RequestVote RPC response.
        """
        rpc = msg.value

        if self.state == State.FOLLOWER:
            return

        if self.state == State.CANDIDATE:

            # If it's append entries, decide whether or not to step down.
            if rpc.type == RType.ACK and rpc.term >= self.currentTerm:
                ## Become a follower
                self.state = State.FOLLOWER

                ## Log the failed election
                self.sim.logger.info(
                    "{} has stepped down as candidate".format(self)
                )

                return

            if rpc.type == RType.VOTE:
                self.votes.vote(msg.source.id, rpc.success)
                if self.votes.has_passed():
                    ## Become the leader
                    self.state = State.LEADER
                    self.timeout.stop()

                    ## Send the leadership change append entries
                    self.send_append_entries()

                    ## Log the new leader
                    self.sim.logger.info(
                        "{} has become raft leader".format(self)
                    )

                return

        elif self.state == State.LEADER:

            # Ignore votes after becoming leader
            if rpc.type == RType.VOTE:
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

    def on_remote_write_rpc(self, message):
        """
        Unpacks the version from the remote write and initiates a local write.
        """
        access = message.value.version

        # Should we check to see if the write failed, e.g. if it wasn't
        # sequential or there was some other confict? Or just write away?
        self.write(access)

        # Send the write response
        self.send(message.source, WriteResponse(self.currentTerm, True, access))

    def on_write_response_rpc(self, message):
        """
        Completes the write if the remote write was successful.
        """
        rpc = message.value
        if rpc.success:
            rpc.access.complete()
