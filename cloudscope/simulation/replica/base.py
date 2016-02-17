# cloudscope.simulation.replica.base
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
        self.versions    = {}
        self.consistency = kwargs.get(
            'consistency', settings.simulation.default_consistency
        )

    def send(self, target, value):
        message = self.pack(target, value)
        event = self.env.timeout(message.delay, value=message)
        event.callbacks.append(target.recv)

        self.sim.logger.debug(
            "message sent at {} from {} to {}".format(
                self.env.now, message.source, message.target
            )
        )

        return event

    def recv(self, event):
        message = event.value
        self.sim.logger.debug(
            "{!r} received by {} at {} from {} ({}ms delayed)".format(
                message.value, message.target, self.env.now, message.source, message.delay
            )
        )

        # Implemented straight from the simulation
        if message.value == "ACK":
            return

        # Send acknowledgement to the sender
        self.send(message.source, "ACK")

        vers = message.value
        if vers.version not in self.versions:
            self.versions[vers.version] = vers

            # Send updates to everyone else.
            for target in self.connections:
                if target != message.source:
                    self.send(target, vers)

    def read(self):
        """
        Performs a read of the latest version either locally or across cloud.
        """
        pass

    def write(self, version):
        """
        Performs a write of the passed in version, locally or across cloud.
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
        return self.label
