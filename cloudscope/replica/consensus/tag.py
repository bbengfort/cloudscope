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
RemoteAccess  = namedtuple('RemoteAccess', 'epoch, objects, access')
TagRequest    = namedtuple('TagRequest', 'epoch, tags, candidate')
Response      = namedtuple('Response', 'epoch, success, objects')
AppendEntries = namedtuple('AppendEntries', 'epoch, tag, owner, entries')

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

        ## Accesses that are in-flight
        ## Maps timestamp (of initial access) to object being accessed
        self.reads  = {}
        self.writes = {}

        ## Initialize the replica
        super(TagReplica, self).__init__(simulation, **kwargs)
        self.state  = State.READY

    ######################################################################
    ## Core Methods (Replica API)
    ######################################################################

    def recv(self, event):
        """
        Before dispatching the message to an RPC specific handler, there are
        some message-wide checks that need to occur. In this case, the replica
        must update its view appropriately.
        """
        message = event.value
        rpc = message.value

        # If RPC request or response contains term > currentTerm
        # Set currentTerm to term and conver to follower.
        if rpc.epoch > self.epoch:
            self.epoch = rpc.epoch
            self.view  = defaultdict(set)

        # Record the received message and dispatch to event handler
        return super(TagReplica, self).recv(event)

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
            # TODO: create send append entries helper
            # TODO: aggregate writes
            for neighbor in self.neighbors():
                self.send(
                    neighbor, AppendEntries(self.epoch, self.view[self], self.id, [(version, self.epoch)])
                )

            # Also interrupt the heartbeat
            self.heartbeat.stop()

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
        while True:
            if self.state == State.READY and self.view[self]:
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
        self.state = State.TAGGING

        # Construct the tag to send out
        if not isinstance(tag, (set, frozenset)):
            tag = frozenset([tag])

        # Request tag with all current tags
        self.tag = frozenset(self.view[self] | tag)
        rpc = TagRequest(self.epoch, self.tag, self)
        for neighbor in self.neighbors():
            self.send(neighbor, rpc)

        # Log the tag acquisition
        self.sim.logger.info(
            "{} is atempting to acquire tag {}".format(self, self.tag)
        )

    def release(self, tag=None):
        """
        Sends out the release tag RPC
        """
        self.state = State.TAGGING

        # Release all currently held tags
        if tag is None: tag = self.view[self]

        # Construct the tag to send out (if specified)
        if not isinstance(tag, (set, frozenset)):
            tag = frozenset([tag])

        # Request the tag release
        self.tag = frozenset(self.view[self] - tag)
        rpc = TagRequest(self.epoch, self.tag, self)
        for neighbor in self.neighbors():
            self.send(neighbor, rpc)

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
            self.tag = None

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
        else:
            raise SimulationException(
                "Unknown Tag Replica State: {!r} set on {}".format(state, self)
            )

    def on_heartbeat_timeout(self):
        """
        Time to send a heartbeat message to all tags.
        """
        # Now do AppendEntries
        for neighbor in self.neighbors():
            self.send(
                neighbor, AppendEntries(self.epoch, self.view[self], self.id, [])
            )

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

    def on_remote_access(self, msg):
        rpc  = msg.value
        name = rpc.objects

        if rpc.access == WRITE:
            name = rpc.objects.name

        if name in self.view[self]:
            return self.send(
                msg.source, Response(self.epoch, True, self.log[name].lastCommit)
            )

        return self.send(
            msg.source, Response(self.epoch, False, None)
        )


    def on_tag_request_rpc(self, msg):
        """
        Respond to a request for a tag acquisition from a server.
        """
        rpc = msg.value

        for tag in rpc.tags:
            owner = self.find_owner(tag)
            if owner is not None and owner.id != rpc.candidate:
                return self.send(
                    msg.source, Response(self.epoch, False, None)
                )

        return self.send(
            msg.source, Response(self.epoch, True, None)
        )

    def on_append_entries_rpc(self, msg):
        rpc = msg.value

        self.view[msg.source] = rpc.tag

        if rpc.entries:
            for version, epoch in rpc.entries:

                # Append the entry to the log
                self.log[version.name].append(version, epoch)

                # Update the versions to compute visibility
                if version: version.update(self)

        return self.send(
            msg.source, Response(self.epoch, True, None)
        )

    def on_response_rpc(self, msg):
        """
        An RPC response can be to a remote access, a release/aquire vote, or
        to an append entries (both write and heartbeat messages).
        """
        rpc = msg.value

        if self.state == State.TAGGING:
            self.votes.vote(msg.source.id, rpc.success)
            if self.votes.has_passed():
                self.view[self] = set(self.tag)
                self.state = State.READY
                self.sim.logger.info(
                    "{} tag goes to: {}".format(self, self.view[self])
                )

                # Record tag length over time
                self.sim.results.update(
                    'tag size', (self.id, self.env.now, len(self.view[self]))
                )

        elif self.state == State.READY:
            pass

        else:
            raise TagRPCException(
                "Response in unknown state: '{}'".format(self.state)
            )
