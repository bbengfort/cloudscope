# cloudscope.replica.consensus.raft
# Implements strong consistency using Raft consensus.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 06:57:45 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: raft.py [c2eb7ed] benjamin@bengfort.com $

"""
Implements strong consistency using Raft consensus.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.simulation.timer import Timer
from cloudscope.replica.store import namespace
from cloudscope.replica import Consistency, State, ReadPolicy
from cloudscope.exceptions import RaftRPCException, SimulationException
from cloudscope.replica.store import MultiObjectWriteLog

from .base import ConsensusReplica
from .election import ElectionTimer, Election

from collections import defaultdict
from collections import namedtuple


##########################################################################
## Module Constants
##########################################################################

## Timers and timing
HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval
ELECTION_TIMEOUT   = settings.simulation.election_timeout

# Other Settings/Policies
READ_POLICY        = settings.simulation.read_policy
AGGREGATE_WRITES   = settings.simulation.aggregate_writes

## RPC Messages
AppendEntries = namedtuple('AppendEntries', 'term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit')
AEResponse    = namedtuple('AEResponse', 'term, success, lastLogIndex, lastCommitIndex')
RequestVote   = namedtuple('RequestVote', 'term, candidateId, lastLogIndex, lastLogTerm')
VoteResponse  = namedtuple('VoteResponse', 'term, voteGranted')
RemoteWrite   = namedtuple('RemoteWrite', 'term, access')
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
        self.cache       = {}

        ## Policies
        self.read_policy = ReadPolicy.get(kwargs.get('read_policy', READ_POLICY))
        self.aggregate_writes = kwargs.get('aggregate_writes', AGGREGATE_WRITES)

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

        # NOTE: Formerly, this was ALWAYS read commit not read latest, now
        # it is set by the read policy on the replica. We previously noted that
        # read committed was one of the key differences from eventual.
        version = self.read_via_policy(access.name)

        # If the version is None, that we haven't read anything!
        if version is None: return access.drop(empty=True)

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
                store a cache copy so that followers can read their own writes.
                cached copy of the write goes away on AppendEntries.
        - if leader: append to log and complete (no leader latency)

        If the write is remote:
        - if follower: log warning and forward to leader
        - if leader: append to log but do not complete (complete at local)

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

            # Write a new version to the latest read by policy
            version = self.write_via_policy(access.name)

            # Update the access with the latest version
            access.update(version)

            # Log the access from this particular replica.
            access.log(self)

            if self.state == State.LEADER:
                # Append to log and complete if leader and local
                self.append_via_policy(access, complete=True)

            else:
                # Store the version in the cache and send remote write.
                self.cache[access.name] = version
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
                self.append_via_policy(access, complete=False)

            else:
                # Remote write occurred from client to a follower
                self.sim.logger.info(
                    "remote write on follower node: {}".format(self)
                )

                # Store the version in the cache and send remote write.
                self.cache[access.name] = version
                return self.send_remote_write(access)

        # At this point we've dealt with local vs. remote, we should be the leader
        assert self.state == State.LEADER

        # Update the version to track visibility latency
        forte = True if settings.simulation.forte_on_append else False
        version.update(self, forte=forte)

        # Now do AppendEntries
        # Also interrupt the heartbeat since we just sent AppendEntries
        if not self.aggregate_writes:
            self.send_append_entries()
            self.heartbeat.stop()

        return access

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

    def send_append_entries(self, target=None):
        """
        Helper function to send append entries to quorum or a specific node.

        Note: fails silently if target is not in the neighbors list.
        """
        # Leader check
        if not self.state == State.LEADER:
            return

        # Go through follower list.
        for node, nidx in self.nextIndex.iteritems():
            # Filter based on the target supplied.
            if target is not None and node != target:
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
                "no leader: dropped write at {}".format(self), color="LIGHT_RED"
            )

            return access.drop()

        # Send the remote write to the leader
        # NOTE: If the send is dropped then the access is also dropped.
        # See self.on_dropped_message for more on that.
        self.send(
            leader, RemoteWrite(self.currentTerm, access)
        )

        return access

    def get_leader_node(self):
        """
        Searches for the leader amongst the neighbors. Raises an exception if
        there are multiple leaders, which is an extreme edge case.
        """
        leaders = [
            node for node in self.quorum() if node.state == State.LEADER
        ]

        if len(leaders) > 1:
            raise SimulationException("MutipleLeaders?!")
        elif len(leaders) < 1:
            return None
        else:
            return leaders[0]

    def read_via_policy(self, name):
        """
        This method returns a version from either the log or the cache
        according to the read policy set on the replica server as follows:

            - COMMIT: return the latest commited version (ignoring cache)
            - LATEST: return latest version in log or in cache

        This method raises an exception on bad read policies.
        """

        # If the policy is read committed, return the latest committed version
        if self.read_policy == ReadPolicy.COMMIT:
            return self.log.get_latest_commit(name)

        # If the policy is latest, read the latest and compare to cache.
        if self.read_policy == ReadPolicy.LATEST:
            # Get the latest version from the log (committed or not)
            version = self.log.get_latest_version(name)

            # If name in the cache and the cache version is greater, return it.
            if name in self.cache and version is not None:
                if self.cache[name] > version:
                    return self.cache[name]

            # Return the latest version
            return version

        # If we've reached this point, we don't know what to do!
        raise SimulationException("Unknown read policy!")

    def write_via_policy(self, name):
        """
        This method returns a new version incremented from either from the
        log or from the cache according to the read policy. It also handles
        any "new" writes, e.g. to objects that haven't been written yet.
        """
        # Fetch the version from the log or the cache according to the
        # read policy. This implements READ COMMITTED/READ LATEST
        latest = self.read_via_policy(name)

        # Perform the write
        if latest is None:
            return namespace(name)(self)

        return latest.nextv(self)

    def append_via_policy(self, access, complete=False):
        """
        This method is the gatekeeper for the log and can implement policies
        like "don't admit forks". It must drop the access if it doesn't meet
        the policy, and complete it if specified.

        NOTE: This is a leader-only method (followers have entries appended
        to their logs via AppendEntries) and will raise an exception if the
        node is not the leader.
        """
        if self.state != State.LEADER:
            raise RaftRPCException(
                "Append via policies called on a follower replica!"
            )

        # The default policy is just append anything
        # NOTE: subclasses (as in Federated) can modify this
        self.log.append(access.version, self.currentTerm)

        # Complete the access if specified by the caller.
        if complete:
            access.complete()

        # Indicate that we've successfully appended to the log
        return True

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
            self.nextIndex   = {node: self.log.lastApplied + 1 for node in self.quorum() if node != self}
            self.matchIndex  = {node: 0 for node in self.quorum() if node != self}
        elif self.state == State.READY:
            # This happens on the call to super, just ignore for now.
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

        for follower in self.quorum():
            if follower == self: continue
            self.send(
                follower, rpc
            )

        # Log the newly formed candidacy
        self.sim.logger.info(
            "{} is now a leader candidate".format(self), color="CYAN"
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
                        "{} voting for {}".format(self, rpc.candidateId), color="YELLOW"
                    )

                    self.timeout.stop()
                    self.votedFor = rpc.candidateId
                    return self.send(
                        msg.source, VoteResponse(self.currentTerm, True)
                    )

        return self.send(
            msg.source, VoteResponse(self.currentTerm, False)
        )

    def on_vote_response_rpc(self, msg):
        """
        Callback for AppendEntries and RequestVote RPC response.
        """
        rpc = msg.value

        if self.state == State.CANDIDATE:

            # Update the current election
            self.votes.vote(msg.source.id, rpc.voteGranted)
            if self.votes.has_passed():
                ## Become the leader
                self.state = State.LEADER
                self.timeout.stop()

                ## Send the leadership change append entries
                self.send_append_entries()

                ## Log the new leader
                self.sim.logger.info(
                    "{} has become raft leader".format(self), color="GREEN"
                )

            return

        elif self.state in (State.FOLLOWER, State.LEADER):
            # Ignore vote responses if we've already been elected.
            return

        else:
            raise RaftRPCException(
                "Vote response in unknown state: '{}'".format(self.state)
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
                msg.source, AEResponse(self.currentTerm, False, self.log.lastApplied, self.log.lastCommit)
            )

        # Reply false if log doesn't contain an entry at prevLogIndex whose
        # term matches previous log term.
        if self.log.lastApplied < rpc.prevLogIndex or self.log[rpc.prevLogIndex].term != rpc.prevLogTerm:
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
                msg.source, AEResponse(self.currentTerm, False, self.log.lastApplied, self.log.lastCommit)
            )

        # At this point AppendEntries RPC is accepted
        rpcInsertIndex = rpc.prevLogIndex + 1
        if self.log.lastApplied >= rpcInsertIndex:
            # If existing entry conflicts with new one (same index, different terms)
            # Delete the existing entry and all that follow it.
            if self.log[rpcInsertIndex].term != rpc.term:
                self.log.truncate(rpcInsertIndex)

        if self.log.lastApplied >= rpcInsertIndex:
            # Possibly a duplicate append entries (or out of order AE)
            # If we're at this point we should have a non-conflicting entry
            # at the insert index. So just return and do nothing with this.
            self.sim.logger.warn((
                "{} received possible out of order append entries "
                "- there exists a non conflicting entry at index {}".format(
                    self, rpcInsertIndex
                )
            ))
            return

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
        if rpc.entries:
            self.sim.logger.debug(
                "{} writes {} at idx {} (term {}, commit {})".format(
                self, self.log.lastVersion, self.log.lastApplied, self.log.lastTerm, self.log.commitIndex
            ))

        # If leaderCommit > commitIndex, update commit Index
        if rpc.leaderCommit > self.log.commitIndex:
            self.log.commitIndex = min(rpc.leaderCommit, self.log.lastApplied)

        # Return success response.
        return self.send(msg.source, AEResponse(self.currentTerm, True, self.log.lastApplied, self.log.lastCommit))

    def on_ae_response_rpc(self, msg):
        """
        Handles acknowledgment of append entries message.
        """
        rpc = msg.value

        if self.state == State.LEADER:

            if rpc.success:
                self.nextIndex[msg.source]  = rpc.lastLogIndex + 1
                self.matchIndex[msg.source] = rpc.lastLogIndex

            else:
                # Set the next index to the follower's previous log index or
                # my
                # Decrement next index and retry append entries
                # Ensure to floor the nextIndex to 1 (the start of the log).
                nidx = self.nextIndex[msg.source] - 1
                self.nextIndex[msg.source] = max(nidx, 1)
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
                        forte = True if settings.simulation.forte_on_commit else False
                        self.log[idx][0].update(self, commit=True, forte=forte)

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
                    "{} has stepped down as candidate".format(self), color="LIGHT_CYAN"
                )

                return

        elif self.state == State.FOLLOWER:
            # Ignore AE messages if we are the follower.
            return

        else:
            raise RaftRPCException(
                "Append entries response in unknown state: '{}'".format(self.state)
            )

    def on_remote_write_rpc(self, message):
        """
        Unpacks the version from the remote write and initiates a local write.
        """

        # Write the access from the remote replica
        access = message.value.access
        self.write(access)

        # Check if the access was dropped (e.g. the write failed)
        success = not access.is_dropped()

        # Send the write response
        self.send(message.source, WriteResponse(self.currentTerm, success, access))

    def on_write_response_rpc(self, message):
        """
        Completes the write if the remote write was successful.
        """
        rpc = message.value
        if rpc.success:
            rpc.access.complete()

    def on_dropped_message(self, target, value):
        """
        Called when there is a network error and a message that is being sent
        is dropped - for Raft, if it was a remote write that was dropped then
        drop the access (for now) rather than retrying later. Ignore for all
        other message types (e.g. the message just gets dropped)
        """

        # Log the dropped message
        super(RaftReplica, self).on_dropped_message(target, value)

        # Drop any writes that can't be sent to the leader.
        if isinstance(value, RemoteWrite):
            self.sim.logger.info(
                "unavailable leader: dropped write at {}".format(self), color="LIGHT_RED"
            )

            value.access.drop()
