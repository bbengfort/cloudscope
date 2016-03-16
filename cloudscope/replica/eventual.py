# cloudscope.replica.eventual
# Implements the anti-entropy and eventual consistency policies on a replica.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Feb 17 06:36:33 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: eventual.py [] benjamin@bengfort.com $

"""
Implements the anti-entropy and eventual consistency policies on a replica.
[Eventual consistency][ec] requires two things:

1. method of exchanging data (anti-entropy)
2. method of reconcilliation

Anti Entropy
============

Writes are gossiped to and from causal/eventual devices for [anti-entropy][gossip]
    - pushed via [rumor-mongering][gp]
    - pulled via periodic gossip
    - random targets in both cases

Writes are always pushed in in-order.
    - first find out what target has (remote read)
    - then push everything the source has at the target (remote write).
    - only new versions are pushed (some devices might not get old versions).

Reconcilliation
===============

Last writer wins. Reconcillation is scheduled via asynchronous repair, e.g.
not part of a read/write operation, and is therefore part of the anti-entropy
mechanism rather than any remote reads/writes.

[ec]: https://en.wikipedia.org/wiki/Eventual_consistency
[gossip]: https://en.wikipedia.org/wiki/Gossip_protocol
[gp]: http://www.inf.u-szeged.hu/~jelasity/ddm/gossip.pdf
"""

##########################################################################
## Imports
##########################################################################

import random

from .base import Replica
from .store import Version

from cloudscope.config import settings
from cloudscope.simulation.timer import Timer

from collections import defaultdict
from collections import namedtuple

# Anti Entropy Delay
AE_DELAY    = settings.simulation.anti_entropy_delay
DO_GOSSIP   = settings.simulation.do_gossip
DO_RUMORING = settings.simulation.do_rumoring

## RPC Messages
Gossip   = namedtuple('Gossip', 'current')
Response = namedtuple('Response', 'latest, success')


##########################################################################
## Eventual Replica
##########################################################################

class EventualReplica(Replica):

    def __init__(self, simulation, **kwargs):
        super(EventualReplica, self).__init__(simulation, **kwargs)

        # Eventually Consistent Settings
        self.ae_delay    = kwargs.get('anti_entropy_delay', AE_DELAY)
        self.do_gossip   = kwargs.get('do_gossip', DO_GOSSIP)
        self.do_rumoring = kwargs.get('do_rumoring', DO_RUMORING)

        # Storage of all versions in the replica and a pointer to the latest.
        self.storage     = {}
        self.current     = None
        self.timeout     = None

    def read(self, name=None):
        """
        Performs a read of the latest version either locally or across cloud.
        """
        name = name.name if isinstance(name, Version) else name
        self.current = self.storage.get(name, None)

        # Record the read latency as zero in eventual
        self.sim.results.update(
            'read latency', (self.id, 0)
        )

        # Record the stale read and return the super.
        return super(EventualReplica, self).read(self.current)

    def write(self, name=None):
        """
        Performs a write to the current version. If no version is passed in,
        the write is assumed to be local, and the current version will be
        forked. If the version is passed in, the write is assumed to be
        remote, and the version will be updated accordingly.
        """

        # Figure out what is being written to the replica
        if isinstance(name, Version):
            # Then this is a remote write
            version = name
            name = version.name

            # Log the remote write
            self.sim.logger.debug(
                "remote write version {} on {}".format(version, self)
            )

        else:
            # This is a local write, fetch correct version from the store.
            version = self.storage.get(name, None) if name is not None else self.current

            # Perform the fork for the write
            version = Version.new(name)(self) if version is None else version.fork(self)

            # Log the local write
            self.sim.logger.info(
                "write version {} on {}".format(self.current, self)
            )

        # Write the new version to the local data store
        self.current = version
        self.storage[name] = version

        # Update the version to track visibility latency
        version.update(self)

    def gossip(self):
        """
        Randomly selects a neighbor and gossips about the latest version.
        """
        # If gossiping is not allowed, forget about it.
        if not self.do_gossip or self.current is None:
            return

        # Randomly select a neighbor from the connections list.
        target = random.choice(self.connections.keys())
        self.send(target, Gossip(self.current))

    def rumor(self):
        """
        Performs on access rumor mongering
        """
        # if rumoring is not allowed, forget about it.
        if not self.do_rumoring or self.current is None:
            return

        raise NotImplementedError("Rumor mongering is not implemented.")

    def get_anti_entropy_timeout(self):
        """
        Creates the anti-entropy timeout
        """
        self.timeout = Timer(self.env, self.ae_delay, self.gossip)
        return self.timeout.start()

    def run(self):
        """
        The run method basically implements an anti-entropy timer.
        """
        while True:
            yield self.get_anti_entropy_timeout()

    def recv(self, event):
        """
        Perform handling of messages for rumor mongering and gossip.
        """
        message = super(EventualReplica, self).recv(event)
        rpc = message.value

        handler = {
            "Gossip": self.on_gossip_rpc,
            "Response": self.on_response_rpc,
        }[rpc.__class__.__name__]

        handler(message)
        return message

    def on_gossip_rpc(self, message):
        """
        Receiving a gossip message from another node.
        """
        rpc = message.value
        response = None

        if self.current is None or rpc.current > self.current:
            self.write(rpc.current)
            response = Response(self.current, True)
        elif rpc.current == self.current:
            response = Response(self.current, True)
        else:
            response = Response(self.current, False)

        # Respond to the sender
        self.send(message.source, response)

    def on_response_rpc(self, message):
        """
        Receiving a gossip response from another node.
        """
        rpc = message.value
        if not rpc.success:
            self.write(rpc.latest)
