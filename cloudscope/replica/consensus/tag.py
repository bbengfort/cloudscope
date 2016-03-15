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
from cloudscope.replica.store import Version
from cloudscope.simulation.timer import Timer
from cloudscope.replica import Replica, Consistency
from cloudscope.exceptions import SimulationException
from cloudscope.exceptions import TagRPCException

from .log import WriteLog
from .election import Election

from collections import defaultdict
from collections import namedtuple
from functools import partial

##########################################################################
## Module Constants
##########################################################################

## Access Enumeration
READ  = "r"
WRITE = "w"

## State Enumeration
READY   = 1
TAGGING = 2

## Timers and timing
SESSION_TIMEOUT    = settings.simulation.session_timeout
HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval

## RPC Messages
RemoteAccess  = namedtuple('RemoteAccess', 'tagset, objects, access')
AcquireTags   = namedtuple('AcquireTags', 'tagset, tags, candidate')
ReleaseTags   = namedtuple('ReleaseTags', 'tagset, tags, candidate')
Response      = namedtuple('Response', 'tagset, success, objects')
AppendEntries = namedtuple('AppendEntries', 'tagset, tags, owner, entries')

##########################################################################
## Tag Replica
##########################################################################

class TagReplica(Replica):

    def __init__(self, simulation, **kwargs):
        ## Initialize the replica
        super(TagReplica, self).__init__(simulation, **kwargs)

        ## Timers for work
        self.session_timeout    = kwargs.get('session_timeout', SESSION_TIMEOUT)
        self.heartbeat_interval = kwargs.get('heartbeat_interval', HEARTBEAT_INTERVAL)
        self.session   = None
        self.heartbeat = None

        ## Initialze the tag specific settings
        self.state  = READY
        self.tagset = 0
        self.log    = defaultdict(WriteLog)
        self.view   = defaultdict(set)

        ## Accesses that are in-flight
        ## Maps timestamp (of initial access) to object being accessed
        self.reads  = {}
        self.writes = {}

    @property
    def neighbors(self):
        """
        Returns the neighbors that are of a medium consistency
        """
        # Filter only connections that are medium
        is_medium = lambda r: r.consistency == Consistency.MEDIUM
        for node in filter(is_medium, self.connections):
            yield node

    @property
    def quorum(self):
        """
        Returns the nodes that are in the tagset quorum (neighbors + self)
        """
        for node in self.neighbors:
            yield node

        # Don't forget to  yield self!
        yield self

    @property
    def state(self):
        """
        Manages the state of the node when being set.
        """
        if not hasattr(self, '_state'):
            self._state = READY
        return self._state

    @state.setter
    def state(self, state):
        """
        Setting the state decides how the Tag node will interact.
        """

        # Do state specific tag modifications
        if state == READY:
            self.votes = None
            self.tag = None

            # Also interrupt the heartbeat
            if self.heartbeat: self.heartbeat.stop()

        elif state == TAGGING:
            # Convert to tag acquisition/release
            self.tagset += 1

            # Create election and vote for self
            self.votes = Election([node.id for node in self.quorum])
            self.votes.vote(self.id)

            # Also interrupt the heartbeat
            if self.heartbeat: self.heartbeat.stop()
        else:
            raise SimulationException(
                "Unknown Tag Replica State: {!r} set on {}".format(state, self)
            )

        # Set the state property on the replica
        self._state = state

    def owns(self, name):
        """
        Returns True if the name is in the current tagset.
        """
        return name in self.view[self]

    def find_owner(self, name):
        """
        Looks up the owner of the name in the current view.
        Returns None if there is no owner fo the tag.
        """
        for owner, tagset in self.view.items():
            if name in tagset:
                return owner
        return None

    def acquire(self, tag):
        """
        Sends out the acquire tag RPC
        """
        self.state = TAGGING

        # Construct the tagset to send out
        if not isinstance(tag, (set, frozenset)):
            tag = frozenset([tag])

        # Request tag with all current tags
        self.tag = frozenset(self.view[self] | tag)
        rpc = AcquireTags(self.tagset, self.tag, self)
        for neighbor in self.neighbors:
            self.send(neighbor, rpc)

        # Log the tag acquisition
        self.sim.logger.info(
            "{} is atempting to acquire tag {}".format(self, self.tag)
        )

    def release(self, tag=None):
        """
        Sends out the release tag RPC
        """
        self.state = TAGGING

        # Release all currently held tags
        if tag is None: tag = self.view[self]

        # Construct the tagset to send out (if specified)
        if not isinstance(tag, (set, frozenset)):
            tag = frozenset([tag])

        # Request the tag release
        self.tag = frozenset(self.view[self] - tag)
        rpc = ReleaseTags(self.tagset, self.tag, self)
        for neighbor in self.neighbors:
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

    def on_heartbeat_timeout(self):
        """
        Time to send a heartbeat message to all tags.
        """
        # Now do AppendEntries
        for neighbor in self.neighbors:
            self.send(
                neighbor, AppendEntries(self.tagset, self.view[self], self.id, [])
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
                msg.source, Response(self.tagset, True, self.log[name].lastCommit)
            )

        return self.send(
            msg.source, Response(self.tagset, False, None)
        )


    def on_acquire_tags(self, msg):
        """
        Respond to a request for a tag acquisition from a server.
        """
        rpc = msg.value

        for tag in rpc.tags:
            owner = self.find_owner(tag)
            if owner is not None and owner.id != rpc.candidate:
                return self.send(
                    msg.source, Response(self.tagset, False, None)
                )

        return self.send(
            msg.source, Response(self.tagset, True, None)
        )

    def on_release_tags(self, msg):
        """
        Respond to a request for a tag release from a server.
        """
        return self.send(msg.source, Response(self.tagset, True, None))

    def on_append_entries(self, msg):
        rpc = msg.value

        self.view[msg.source] = rpc.tags

        if rpc.entries:
            for version, tagset in rpc.entries:

                # Append the entry to the log
                self.log[version.name].append(version, tagset)

                # Update the versions to compute visibility
                if version: version.update(self)

        return self.send(
            msg.source, Response(self.tagset, True, None)
        )

    def on_rpc_response(self, msg):
        """
        An RPC response can be to a remote access, a release/aquire vote, or
        to an append entries (both write and heartbeat messages).
        """
        rpc = msg.value

        if self.state == TAGGING:
            self.votes.vote(msg.source.id, rpc.success)
            if self.votes.has_passed():
                self.view[self] = set(self.tag)
                self.state = READY
                self.sim.logger.info(
                    "{} tag goes to: {}".format(self, self.view[self])
                )

                # Record tag length over time
                self.sim.results.update(
                    'tag size', (self.id, self.env.now, len(self.view[self]))
                )

        elif self.state == READY:
            pass

        else:
            raise TagRPCException(
                "Response in unknown state: '{}'".format(self.state)
            )

    def recv(self, event):
        """
        Passes messages to their appropriate message handlers.
        """
        message = event.value
        rpc = message.value

        # If RPC request or response contains term > currentTerm
        # Set currentTerm to term and conver to follower.
        if rpc.tagset > self.tagset:
            self.tagset = rpc.tagset

        handler = {
            "RemoteAccess": self.on_remote_access,
            "AcquireTags": self.on_acquire_tags,
            "ReleaseTags": self.on_release_tags,
            'AppendEntries': self.on_append_entries,
            "Response": self.on_rpc_response,
        }[rpc.__class__.__name__]

        handler(message)

    def read(self, name=None):
        """
        Performs a read for the named object.
        """

        # Are we the owner of this tag?
        if self.owns(name):

            self.handle_session()
            version = self.log[name].lastCommit

            if version and version.is_stale():
                # Count the number of stale reads
                self.sim.results.update(
                    'stale reads', (self.id, self.env.now)
                )

                self.sim.logger.info(
                    "stale read of version {} on {}".format(version, self)
                )

            # Record the read latency as zero
            self.sim.results.update(
                'read latency', (self.id, 0)
            )

            return

        # We're going to have some read latency
        self.reads[int(self.env.now)] = name

        # Is there a different owner for the tag?
        owner = self.find_owner(name)
        if owner is not None:
            # If so, send a remote access to them
            return self.send(
                owner, RemoteAccess(self.tagset, name, READ)
            )

        # Request the ownership of the tag
        self.acquire(name)

    def write(self, name=None):
        """
        Performs a write for the named object (very similar to read).
        """
        if isinstance(name, Version):
            # Then this is a remote write
            version = name
            name = version.name

            # Log the remote write
            self.sim.logger.info(
                "remote write version {} on {}".format(version, self)
            )
        else:
            # Then this is a local write
            version = self.log[name].lastVersion
            version = Version.new(name)(self) if version is None else version.fork(self)

            # Log the write
            self.sim.logger.info(
                "write version {} on {}".format(version, self)
            )

        # Are we the owner of this tag?
        if self.owns(name):
            # Reset the session
            self.handle_session()
            # Perform the append entries
            self.log[name].append(version, self.tagset)
            # Update the version to track visibility latency
            version.update(self)

            # Now do AppendEntries
            for neighbor in self.neighbors:
                self.send(
                    neighbor, AppendEntries(self.tagset, self.view[self], self.id, [(version, self.tagset)])
                )

            # Also interrupt the heartbeat
            self.heartbeat.stop()

            return

        # Is there a different owner for the tag?
        owner = self.find_owner(name)
        if owner is not None:
            # If so, send a remote access to them
            return self.send(
                owner, RemoteAccess(self.tagset, version, WRITE)
            )

        # We're going to have some write latency
        self.writes[int(self.env.now)] = version

        # Request the ownership of the tag
        self.acquire(name)

    def run(self):
        while True:
            if self.state == READY and self.view[self]:
                self.heartbeat = Timer(
                    self.env, self.heartbeat_interval, self.on_heartbeat_timeout
                )
                yield self.heartbeat.start()
            else:
                yield self.env.timeout(35)
