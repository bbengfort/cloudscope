# cloudscope.replica.consensus.tag
# Package that implements tag based consensus consistency.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Mar 08 14:28:05 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: tag.py [] benjamin@bengfort.com $

"""
Package that implements tag based consensus consistency.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.simulation.timer import Timer
from cloudscope.replica import Consistency, State
from cloudscope.exceptions import TagRPCException
from cloudscope.exceptions import SimulationException
from cloudscope.replica.store import Version
from cloudscope.replica.store import WriteLog
from cloudscope.utils.enums import Enum

from .base import ConsensusReplica
from .election import Election

from collections import defaultdict
from collections import namedtuple
from functools import partial

##########################################################################
## Module Constants
##########################################################################

## Timers and timing
SESSION_TIMEOUT    = settings.simulation.session_timeout
HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval

## RPC Messages
## NOTE: tag should be a data structure of {objects: {index, epoch, commit}}
## NOTE: index, epoch, commit are meaningful in different RPC contexts

RequestTag     = namedtuple('RequestTag', 'epoch, tag, candidate')
TagResponse    = namedtuple('TagResponse', 'epoch, accept')
AppendEntries  = namedtuple('AppendEntries', 'epoch, owner, tag, entries')
AEResponse     = namedtuple('AEResponse', 'epoch, success, tag, reason')
RemoteAccess   = namedtuple('RemoteAccess', 'epoch, access')
AccessResponse = namedtuple('AccessResponse', 'epoch, success, access')

## Sent with RPC messages to indicate the state of a log per object.
LogState       = namedtuple('TagState', 'index, epoch, commit')

## Sent with Append Entries responses to indicate what went wrong.
Reason         = Enum('Reason', 'OK, EPOCH, LOG')


##########################################################################
## Tag Replica
##########################################################################

class TagReplica(ConsensusReplica):

    def __init__(self, simulation, **kwargs):
        ## Timers for work
        self.session_timeout    = kwargs.get('session_timeout', SESSION_TIMEOUT)
        self.heartbeat_interval = kwargs.get('heartbeat_interval', HEARTBEAT_INTERVAL)
        self.session   = None
        self.heartbeat = None

        ## Initialze the tag specific settings
        self.epoch  = 0
        self.log    = defaultdict(WriteLog)
        self.view   = defaultdict(set)

        ## Owner state
        self.nextIndex  = None
        self.matchIndex = None

        ## Initialize the replica
        super(TagReplica, self).__init__(simulation, **kwargs)
        self.state  = State.READY

    ######################################################################
    ## Core Methods (Replica API)
    ######################################################################

    def read(self, name, **kwargs):
        """
        When a tag replica performs a read it has to decide whether or not to
        read locally or to make a remote read across the cluster.

        Convert the read into an access, then check if we own the object.
        If we do, then return the latest commit.
        If we don't and no one else does either, attempt to acquire the tag.
        If we don't and someone else does then either drop, wait, or remote.

        Current implementation: #2, MR, no remote access.
        If someone else owns tag, reads are dropped.

        TODO: Remote vs Local Reads
        """
        # Create the read event using super.
        access = super(TagReplica, self).read(name, **kwargs)

        # Record the number of attempts for the access
        if access.is_local_to(self): access.attempts += 1

        # Increase the session on access.
        self.handle_session()

        # Are we the owner of this tag?
        if self.owns(access.name):
            # TODO: Change to last commit!
            version = self.log[access.name].lastVersion

            # If the version is None, bail since we haven't read anything
            if version is None: return

            # Update the version, complete the read, and log the access
            access.update(version, completed=True)
            access.log(self)

            # Return, we're done reading!
            return access

        # Is there a different owner for the tag?
        owner = self.find_owner(access.name)
        if owner is not None:
            # Right now just drop the read on its face.
            self.sim.logger.info(
                "ownership conflict: dropped {} at {}".format(access, self)
            )
            return

        # We're going to acquire the tag!
        else:
            # Log the access from this particular replica.
            access.log(self)

            # We're going to have some read latency, retry the read.
            retry = Timer(
                self.env, self.heartbeat_interval, lambda: self.read(access)
            ).start()

            if access.attempts <= 1 and self.state != State.TAGGING:
                # Request the ownership of the tag
                self.acquire(access.name)

    def write(self, name, **kwargs):
        """
        When a replica performs a write it needs to decide if it can write to
        the tag locally, can acquire a tag for this object, or if it has to do
        something else like drop, wait, or remote write.

        If the access is local:

            - if the replica owns the tag, append and complete
            - if someone else owns the tag then drop, wait, or remote
            - if no one owns the tag, then attempt to acquire it

        If access is remote:

            - if we own the tag, then append but do not complete (at local)
            - if someone else owns the tag, log and forward to owner
            - if no one owns the tag then respond false
        """
        # Create the read event using super.
        access = super(TagReplica, self).write(name, **kwargs)

        # Increase the session on access.
        self.handle_session()

        # Determine if the write is local or remote
        if access.is_local_to(self):
            # Record the number of attempts for the access
            access.attempts += 1

            # Fetch the latest version from the log.
            latest = self.log[access.name].lastVersion

            # Perform the write
            if latest is None:
                version = Version.new(access.name)(self)
            else:
                version = latest.nextv(self)

            # Update the access with the latest version
            access.update(version)

        else:
            # If there is no version, raise an exception
            if access.version is None:
                raise AccessError(
                    "Attempting a remote write on {} without a version!".format(self)
                )

            # Save the version variable for use below.
            version = access.version

        # Log the access at this replica
        access.log(self)

        # Are we the owner of this tag?
        if self.owns(access.name):
            # Perform the append entries
            self.log[name].append(version, self.epoch)
            # Update the version to track visibility latency
            version.update(self)

            # Complete the access if it was local
            if access.is_local_to(self): access.complete()

            # Now do AppendEntries
            # Also interrupt the heartbeat since we just sent AppendEntries
            if not settings.simulation.aggregate_writes:
                self.send_append_entries()
                if self.heartbeat: self.heartbeat.stop()

            return

        # Is there a different owner for the tag?
        owner = self.find_owner(name)
        if owner is not None:
            # Right now just drop the write on its face.
            self.sim.logger.info(
                "ownership conflict: dropped {} at {}".format(access, self)
            )
            return

        # We're going to acquire the tag!
        else:
            # We're going to have some write latency, retry the write.
            retry = Timer(
                self.env, self.heartbeat_interval, lambda: self.write(access)
            ).start()

            # Request the ownership of the tag
            self.acquire(access.name)

    def run(self):
        """
        We have to check in at every heartbeat interval. If we own a tag then
        send a heartbeat message, otherwise just keep quiescing.
        """
        while True:
            if self.state == State.OWNER:
                self.heartbeat = Timer(
                    self.env, self.heartbeat_interval, self.on_heartbeat_timeout
                )
                yield self.heartbeat.start()
            else:
                yield self.env.timeout(self.heartbeat_interval)

    ######################################################################
    ## Helper Methods
    ######################################################################

    def owns(self, name):
        """
        Returns True if the name is in the current view for that owner.
        """
        return name in self.view[self]

    def find_owner(self, name):
        """
        Looks up the owner of the name in the current view.
        Returns None if there is no owner fo the tag.
        """
        for owner, tag in self.view.items():
            if name in tag:
                return owner
        return None

    def acquire(self, tag):
        """
        Sends out the acquire tag RPC
        """
        # Construct the tag to send out
        if not isinstance(tag, (set, frozenset)):
            tag = frozenset([tag])

        # Make sure to request the tag we already have
        tag = frozenset(self.view[self] | tag)

        # Request tag with all current tags
        self.send_tag_request(tag)

        # Log the tag acquisition
        self.sim.logger.info(
            "{} is atempting to acquire tag {}".format(self, self.tag)
        )

    def release(self, tag=None):
        """
        Sends out the release tag RPC
        """
        # Release all currently held tags
        if tag is None: tag = self.view[self]

        # Construct the tag to send out (if specified)
        if not isinstance(tag, (set, frozenset)):
            tag = frozenset([tag])

        # Request the difference of the tags we already have
        tag = frozenset(self.view[self] - tag)

        # Request tag with all current tags
        self.send_tag_request(tag)

        # Log the tag release
        self.sim.logger.info(
            "{} is atempting to release tag {}".format(self, tag)
        )

    def handle_session(self):
        """
        Starts a session timer if one isn't running, otherwise resets the
        currently running session timer on an additional access.
        """
        if not self.session:
            self.session = Timer(
                self.env, self.session_timeout,
                partial(self.on_session_timeout, self.env.now)
            )
        else:
            self.session = self.session.reset()

    def get_log_state(self, tag=None):
        """
        Constructs a log state object for append entries responses, either
        for the current tag or simply the current view.
        """
        if tag is None:
            tag = [obj for view in self.view.values() for obj in view]

        return {
            obj: LogState(
                self.log[obj].lastApplied,
                self.log[obj].lastTerm,
                self.log[obj].commitIndex
            ) for obj in tag
        }

    def send_tag_request(self, tag):
        """
        Broadcasts a tag request for the passed in tag.
        """
        # Change state to tagging and save tag locally
        self.state = State.TAGGING
        self.tag = tag

        # Request the entire tag in your current view.
        tagset = {
            owner.id: tagset
            for owner, tagset in self.view.items()
        }
        tagset[self.id] = self.tag

        # Send the tag request RPC to each neighbor
        rpc = RequestTag(self.epoch, tagset, self)
        for neighbor in self.neighbors():
            self.send(neighbor, rpc)

    def send_append_entries(self, target=None):
        """
        Helper function to send append entries to quorum or a specific node.

        Note: fails silently if target is not in the neighbors list.
        """
        # ownership check
        if not self.state == State.OWNER:
            return

        # Go through follower list.
        for node, objs in self.nextIndex.iteritems():
            # Filter based on the target supplied.
            if target is not None and node != target:
                continue

            # Construct the entries, or empty for heartbeat
            # The tag contains the state of each item to be sent
            entries = defaultdict(list)
            tag = defaultdict(LogState)

            for obj, nidx in objs.items():
                # A rule directly from the Raft paper
                if self.log[obj].lastApplied >= nidx:
                    entries[obj] = self.log[obj][nidx:]

                # Compute the previous log index and term
                prevLogIndex = nidx - 1
                prevLogTerm  = self.log[obj][prevLogIndex].term
                commitIndex  = self.log[obj].commitIndex

                # Create the tag state
                tag[obj] = LogState(prevLogIndex, prevLogTerm, commitIndex)

            # Send the append entries message
            self.send(
                node, AppendEntries(
                    self.epoch, self.id, tag, entries
                )
            )

    ######################################################################
    ## Event Handlers
    ######################################################################

    def on_state_change(self):
        """
        Setting the state decides how the Tag node will interact.
        """

        # Do state specific tag modifications
        if self.state == State.READY:
            self.votes = None
            self.tag   = None

            # Remove owner state
            self.nextIndex  = None
            self.matchIndex = None

            # Also interrupt the heartbeat
            if self.heartbeat: self.heartbeat.stop()

        elif self.state == State.TAGGING:
            # Convert to tag acquisition/release
            self.epoch += 1

            # Create election and vote for self
            self.votes = Election([node.id for node in self.quorum()])
            self.votes.vote(self.id)

            # Also interrupt the heartbeat
            if self.heartbeat: self.heartbeat.stop()

        elif self.state == State.OWNER:

            # Create the next index and match index
            self.nextIndex = {
                node: {
                    obj: self.log[obj].lastApplied + 1
                    for obj in self.view[self]
                } for node in self.neighbors()
            }

            self.matchIndex = {
                node: {
                    obj: 0 for obj in self.view[self]
                } for node in self.neighbors()
            }

        else:
            raise SimulationException(
                "Unknown Tag Replica State: {!r} set on {}".format(state, self)
            )

    def on_heartbeat_timeout(self):
        """
        Time to send a heartbeat message to all tags.
        """
        if not self.state == State.OWNER:
            return

        # Send heartbeat or aggregated writes
        self.send_append_entries()

    def on_session_timeout(self, started):
        """
        If the session times out then go ahead and release the tag.
        """
        duration = self.env.now - started

        self.sim.logger.info(
            "session on {} terminated at {} ({} ms)".format(
                self.id, self.env.now, duration
            )
        )

        self.sim.results.update(
            'session length', (self.id, duration)
        )

        self.session = None
        self.release()

    def on_request_tag_rpc(self, msg):
        """
        Respond to a request for a tag acquisition from a server.
        """
        rpc = msg.value
        accept = True

        # The requested epoch must be less than or greater than local.
        if rpc.epoch < self.epoch: accept = False

        # Ensure that no one else owns the tag in your current view.
        for candidate, tagset in rpc.tag.items():
            # Short circuit
            if not accept: break

            for tag in tagset:
                owner = self.find_owner(tag)
                if owner is not None and owner.id != candidate:
                    accept = False
                    break

        # Log the vote decision
        amsg = "accepted" if accept else "did not accept"
        lmsg = "{} {} tag [{}] for {}".format(
            self, amsg, ",".join(rpc.tag[rpc.candidate.id]), rpc.candidate.id
        )
        self.sim.logger.info(lmsg)

        # Send the vote response back to the tag requester
        return self.send(
            msg.source, TagResponse(self.epoch, accept)
        )

    def on_tag_response_rpc(self, msg):
        """
        Handle the votes from tag requests to other nodes.
        """
        rpc = msg.value

        if self.state == State.TAGGING:
            # If the epoch is greater than the current epoch
            if rpc.epoch > self.epoch:
                # Retry the tag request
                self.epoch = rpc.epoch
                self.send_tag_request(self.tag)

                self.sim.logger.info(
                    "{} retrying tag request for {}".format(self, self.tag)
                )

                # Exit: no more work required!
                return

            # Update the current election
            self.votes.vote(msg.source.id, rpc.accept)
            if self.votes.has_passed():

                # Update our local tag and become owner.
                if self.tag:
                    self.state = State.OWNER
                    self.view[self] = set(self.tag)
                else:
                    self.state = State.READY

                # Send out the ownership change append entries
                self.send_append_entries()

                # Log the new tag owner
                self.sim.logger.info(
                    "{} tag goes to: {}".format(self, self.view[self])
                )

                # Record tag length over time
                self.sim.results.update(
                    'tag size', (self.id, self.env.now, len(self.view[self]))
                )

        elif self.state in (State.READY, State.OWNER):
            # Ignore vote responses if we've changed our state
            return

        else:
            raise TagRPCException(
                "Tag request response in unknown state: '{}'".format(self.state)
            )

    def on_append_entries_rpc(self, msg):
        rpc = msg.value

        # reply false if the epoch < current epoch
        if rpc.epoch < self.epoch:
            self.sim.logger.info(
                "{} doesn't accept append entries in epoch {} for epoch {}".format(
                    self, self.epoch, rpc.epoch
                )
            )

            # Send back the request that you made originally.
            return self.send(
                msg.source, AEResponse(
                    self.epoch,
                    {obj: False for obj in rpc.tag.keys()},
                    rpc.tag, Reason.EPOCH
                )
            )

        # Update the view to match the view of the append entries
        # Update the epoch to match the rpc of the append entries
        self.view[msg.source] = set(rpc.tag.keys())
        if self.epoch < rpc.epoch:
            self.epoch = rpc.epoch

        # Now for each object in the RPC, perform Raft-like append entries.
        # The success tracking is a complete tracking for all objects, will
        # return false even if we need to update the log for only one thing.
        # We will reply back with a state object that has per-object details.
        success = defaultdict(bool)
        state   = defaultdict(LogState)

        for obj, prev in rpc.tag.items():
            entries = rpc.entries[obj]
            objlog  = self.log[obj]

            # If log doesn't contain an entry at prev index matching epoch.
            if objlog.lastApplied < prev.index or objlog[prev.index].term != prev.epoch:

                # Perform the logging of this state failure
                if objlog.lastApplied < prev.index:
                    self.sim.logger.info(
                        "{} doesn't accept append to {} index {} where last applied is {}".format(
                            self, obj, prev.index, objlog.lastApplied
                        )
                    )
                else:
                    self.sim.logger.info(
                        "{} doesn't accept append to {} due to epoch mismatch: {} vs {}".format(
                            self, obj, prev.epoch, objlog[prev.index].term
                        )
                    )

                # Mark that there is a problem and continue
                success[obj] = False
                state[obj] = LogState(objlog.lastApplied, objlog.lastTerm, objlog.lastCommit)
                continue

            # At this point the entries are accepted because of continue statements
            if entries:
                if objlog.lastApplied >= prev.index:
                    # If existing entry conflicts with a new one (same index, different epochs)
                    # Delete the existing entry and all that follow it.
                    if objlog[prev.index].term != prev.epoch:
                        objlog.remove(prev.index)

                if objlog.lastApplied > prev.index:
                    # Better look into what's happening here!
                    raise TagRPCException(
                        "{} is possibly receiving duplicate append entries".format(self)
                    )

                # Append any new entries not already in the log.
                for entry in entries:
                    # Add the entry/epoch to the log
                    objlog.append(*entry)

                    # Update the versions to compute visibilities
                    entry[0].update(self)

                # Log the last write from the append entries
                self.sim.logger.debug(
                    "appending {} entries to {} log on {} (term {}, commit {})".format(
                        len(entries), obj, self, objlog.lastTerm, objlog.commitIndex
                    )
                )

            # Update the commit index and save the state of the object.
            if prev.commit > objlog.commitIndex:
                objlog.commitIndex = min(prev.commit, objlog.lastApplied)

            success[obj] = True
            state[obj] = LogState(objlog.lastApplied, objlog.lastTerm, objlog.lastCommit)

        # Return the response back to the owner
        reason = Reason.OK if all(success.values()) else Reason.LOG
        return self.send(
            msg.source, AEResponse(self.epoch, success, state, reason)
        )

    def on_ae_response_rpc(self, msg):
        """
        Handles acknowledgment of append entries messages.
        """
        rpc = msg.value
        retry = False

        if self.state == State.OWNER:

            # Update state of followers in the tag group
            for obj, success in rpc.success.items():
                if success:
                    self.nextIndex[msg.source][obj] = rpc.tag[obj].index + 1
                    self.matchIndex[msg.source][obj] = rpc.tag[obj].index

                else:
                    # If the epoch is not the same, update accordingly.
                    if rpc.epoch > self.epoch:
                        self.epoch = rpc.epoch

                    # If the failure was because of the epoch, simply retry.
                    if rpc.reason == Reason.EPOCH:
                        retry = True

                    # Otherwise decrement the next index and to retry
                    elif rpc.reason == Reason.LOG:
                        self.nextIndex[msg.source][obj] -= 1
                        retry = True

                    else:
                        raise TagRPCException(
                            "Unknown append entries failure reason: {}".format(rpc.reason)
                        )

            # Determine if we can commit the entry
            for obj, state in rpc.tag.items():
                log = self.log[obj]
                for n in xrange(log.lastApplied, log.commitIndex, -1):
                    commit = Election(self.matchIndex.keys())
                    for node, objs in self.matchIndex.items():
                        match = objs[obj]
                        commit.vote(node, match >= n)

                    if commit.has_passed() and log[n].term == self.epoch:
                        # Commit all versions from the last log to now.
                        for idx in xrange(log.commitIndex, n+1):
                            if not log[idx].version: continue
                            log[idx].version.update(self, commit=True)

                        # Set the commit index and break
                        log.commitIndex = n
                        break

            # If retry, send append entries back to the source.
            if retry: self.send_append_entries(msg.source)


        elif self.state == State.TAGGING:
            # Determine if we need to retry the tagging again.
            if rpc.epoch > self.epoch:
                # Retry the tag request
                self.epoch = rpc.epoch
                self.send_tag_request(self.tag)

                self.sim.logger.info(
                    "{} retrying tag request for {}".format(self, self.tag)
                )

                return

        elif self.state == State.READY:
            # Ignore AE messages if we're not an owner anymore.
            return

        else:
            raise TagRPCException(
                "Response in unknown state: '{}'".format(self.state)
            )

    def on_remote_access(self, msg):
        """
        Handles remote writes to and from the replicas.
        """
        access = msg.value.access

        # Ensure that we own the object
        if not self.owns(access.name):
            return self.send(
                msg.source, AccessResponse(self.epoch, False, access)
            )

        # If we do own the object, then respond:
        method = {
            'read': self.read,
            'write': self.write,
        }[access.type]

        # Call the remote method with the access.
        method(access)

        return self.send(
            msg.source, AccessResponse(self.epoch, True, access)
        )

    def on_access_response_rpc(self, msg):
        """
        Handles responses to remote accesses.
        """
        rpc = msg.value
        if rpc.success:
            rpc.access.complete()
