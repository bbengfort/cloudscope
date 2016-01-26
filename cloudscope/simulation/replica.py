# cloudscope.simulation.replica
# Base functionality for a replica on a personal cloud storage system.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 06:05:58 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: replica.py [] benjamin@bengfort.com $

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

    def __init__(self, parent, **kwargs):
        # Initialze Node
        super(Replica, self).__init__()

        # Simulation Environment
        self.sim = parent

        # Replica Properties
        self.id    = kwargs.get('id', 'r{}'.format(self.counter.next()))
        self.type  = kwargs.get('type', settings.simulation.default_replica)
        self.label = kwargs.get('label', "{}-{}".format(self.type, self.id))
        self.location    = kwargs.get('location', Location.UNKNOWN)
        self.versions    = {}
        self.consistency = kwargs.get(
            'consistency', settings.simulation.default_consistency
        )

    @property
    def env(self):
        return self.sim.env

    def send(self, target, value):
        message = self.pack(target, value)
        event = self.env.timeout(message.delay, value=message)
        event.callbacks.append(target.recv)

        self.sim.logger.debug(
            "message sent at {} from {} to {}".format(
                self.env.now, message.source, message.target
            )
        )

    def recv(self, event):
        message = event.value
        self.sim.logger.debug(
            "{!r} received by {} at {} from {} ({}ms delayed)".format(
                message.value, message.target, self.env.now, message.source, message.delay
            )
        )

    def serialize(self):
        return dict([
            (attr, getattr(self, attr))
            for attr in (
                'id', 'type', 'label', 'location', 'consistency', 'versions'
            )
        ])

    def __str__(self):
        return self.label

##########################################################################
## Version Objects
##########################################################################

class Version(object):
    """
    Implements a representation of the tree structure for a file version.
    """

    # Autoincrementing ID
    counter = Sequence()

    def __init__(self, replica, parent=None, **kwargs):
        """
        Creation of an initial version for the version tree.
        """
        self.writer   = replica
        self.parent   = parent
        self.version  = self.counter.next()
        self.level    = kwargs.get('level', replica.consistency)
        self.created  = kwargs.get('created', replica.env.now)
        self.updated  = kwargs.get('updated', replica.env.now)

    def fork(self, replica, **kwargs):
        """
        Creates a fork of this version
        """
        return Version(
            replica, parent=self, level=self.level, created=self.created
        )
