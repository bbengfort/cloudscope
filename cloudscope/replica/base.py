# cloudscope.simulation.base
# Base functionality for a replica on a personal cloud storage system.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 06:05:58 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: base.py [] benjamin@bengfort.com $

"""
Base functionality for a replica on a personal cloud storage system.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.dynamo import Sequence
from cloudscope.simulation.network import Node

class Consistency(object):

    STRONG = "strong"
    MEDIUM = "medium"
    LOW    = "low"

class Location(object):

    HOME    = "home"
    WORK    = "work"
    MOBILE  = "mobile"
    CLOUD   = "cloud"
    UNKNOWN = "unknown"

##########################################################################
## Replica Functionality
##########################################################################

class Replica(Node):
    """
    A replica is a network node that implements version handling.
    """

    # Known Replica Types
    DESKTOP = "desktop"
    STORAGE = "storage"
    LAPTOP  = "laptop"
    TABLET  = "tablet"
    PHONE   = "smartphone"

    # Autoincrementing ID
    counter = Sequence()

    def __init__(self, sim, **kwargs):
        # Initialze Node
        super(Replica, self).__init__(sim.env)

        # Simulation Environment
        self.sim = sim

        # Replica Properties
        self.id    = kwargs.get('id', 'r{}'.format(self.counter.next()))
        self.type  = kwargs.get('type', settings.simulation.default_replica)
        self.label = kwargs.get('label', "{}-{}".format(self.type, self.id))
        self.location    = kwargs.get('location', Location.UNKNOWN)
        self.consistency = kwargs.get(
            'consistency', settings.simulation.default_consistency
        )

    def send(self, target, value):
        """
        Simply logs that the message has been sent.
        """
        event = super(Replica, self).send(target, value)
        message = event.value
        mtype = message.value.__class__.__name__ if message.value else "None"

        self.sim.logger.debug(
            "message {} sent at {} from {} to {}".format(
                mtype, self.env.now, message.source, message.target
            )
        )

        # Track time series of sent messages
        if settings.simulation.count_messages:
            self.sim.results.update(
                "sent", (self.id, self.env.now, mtype)
            )

        # Track total number of sent messages
        self.sim.results.messages['sent'][mtype] += 1
        return event

    def recv(self, event):
        """
        Simply logs that the message has been received.
        """
        # Get the unpacked message from the event.
        message = super(Replica, self).recv(event)
        mtype = message.value.__class__.__name__ if message.value else "None"

        self.sim.logger.debug(
            "protocol {!r} received by {} from {} ({}ms delayed)".format(
                mtype, message.target, message.source, message.delay
            )
        )

        # Track time series of recv messages
        if settings.simulation.count_messages:
            self.sim.results.update(
                "recv", (self.id, self.env.now, mtype, message.delay)
            )

        # Track total number of recv messages
        self.sim.results.messages['recv'][mtype] += 1
        return message

    def read(self, version=None):
        """
        Intended as a stub method to record a read on the replica. This
        method wil take the version "read" from a subclass and record if it's
        stale, as well as the read latency if the object is an event.

        Returns the read event object or None.
        """
        if version is not None:
            read = version.read(self, completed=True)

            if read.is_stale():
                # Log the stale read
                self.sim.logger.info(
                    "stale read of version {} on {}".format(version, self)
                )

            return read

    def write(self, version=None):
        """
        Performs a write to the local version or writes the version to disk.
        """
        pass

    def serialize(self):
        return dict([
            (attr, getattr(self, attr))
            for attr in (
                'id', 'type', 'label', 'location', 'consistency'
            )
        ])

    def __str__(self):
        return "{} ({})".format(self.label, self.id)
