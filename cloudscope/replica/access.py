# cloudscope.replica.access
# Wrappers for access events (reads and writes) passed to replicas.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Apr 04 10:17:32 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: access.py [] benjamin@bengfort.com $

"""
Wrappers for access events (reads and writes) passed to replicas.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.utils.decorators import Countable
from cloudscope.exceptions import AccessError


##########################################################################
## Module Constants
##########################################################################

# Access types
READ  = "read"
WRITE = "write"

##########################################################################
## Base Access Event
##########################################################################

class Access(object):
    """
    Represents an access event (either a read or a write) and acts as a
    closure for the event (e.g. retries). An access event should be created
    by the replica when read/write is called (not passed to the method).
    However, other processes (like the workload) can use them for management
    purposes if required.

    The access event has three primary parts:

    1. The name of the object being accessed (the name not the version).
    2. The replica server doing the accessing (accessor)
    3. The version that is eventually read or written to.

    The access uses the replica object to get access to the simulation for
    logging results - and in fact all access results are recorded through an
    Access subclass instance.

    This means that Accesses have a lot of similarity to Version objects, but
    the work that used to be in the version should be decoupled and added to
    the access for more precise control of results logging.
    """

    __metaclass__ = Countable

    @classmethod
    def create(cls, name_or_access, replica, **kwargs):
        """
        Helper to quickly create an access from a name (just a pass through
        to the constructor), but with some logic to detect if the name is
        already an access event (in the case of remote reads/writes).
        """
        if isinstance(name_or_access, cls):
            return name_or_access
        return cls(name_or_access, replica, **kwargs)

    def __init__(self, name, replica, version=None, **kwargs):
        """
        Creation of access event with three primary parts, all others are
        fetched off of the keyword arguments.
        """

        # Keep track of the number of accesses of each type.
        self.id = self.counter.next()

        self.name    = name      # name of the object being accessed
        self.owner   = replica   # the origination server of the access
        self.version = version   # the version that is returned by the access
        self.dropped = False     # if the access has been dropped or not

        # Timestamps added for ease of use
        self.started  = kwargs.get('started', self.env.now)
        self.finished = kwargs.get('finished', None)

        # Log retried accesses (if required)
        self.attempts = 0

        # We can create completed accesses for quick requests
        if kwargs.get('completed', False):
            self.complete()

    @property
    def env(self):
        """
        Returns the environment, through the owner.
        """
        return self.owner.env

    @property
    def sim(self):
        """
        Returns the simulation, through the owner.
        """
        return self.owner.sim

    @property
    def latency(self):
        """
        Computes the access latency as the difference between start and finish
        """
        if self.is_completed() or self.is_dropped():
            return self.finished - self.started

    @property
    def type(self):
        """
        Returns the access type (read or write).
        """
        return self.__class__.__name__.lower()

    def is_dropped(self):
        """
        Checks if the access has been dropped
        """
        return self.dropped

    def is_completed(self):
        """
        Checks if the access has been completed (correctly)
        """
        return self.version is not None and self.finished is not None

    def is_local_to(self, replica):
        """
        Helper to check if the access is local to the passed in replica by
        comparing the replica with the owner of the access.
        """
        return replica == self.owner

    def is_remote_to(self, replica):
        """
        Helper to check if the access is remote to the passed in replica.
        Should return the opposite of `is_local_to`.
        """
        return replica != self.owner

    def drop(self):
        """
        An access drop is a bad thing, but in some cases, replicas might just
        drop or ignore the previous access. This method tracks that.
        """
        self.dropped = True
        self.finished = self.env.now
        return self

    def update(self, version, completed=False):
        """
        Updates the access with a version (e.g. when preparing to send back
        a remote access, add the version of that access).

        There are also some shortcut flags for multiple calls:
        if completed: also call complete (e.g. for quick local updates)
        """
        self.version = version
        if completed: self.complete()
        return self

    def complete(self):
        """
        Completes the read and triggers the logging and metric reporting.
        Subclasses should handle this more specifically.
        """
        # Don't call complete multiple times.
        if self.is_completed():
            raise AccessError(
                "Attempting to complete {} after it was already completed!".format(self)
            )

        if self.version is None:
            raise AccessError(
                "Attempting to complete {} without an associated version!".format(self)
            )

        self.finished = self.env.now
        return self

    def log(self, replica):
        """
        Helper function to write a log record about an access on a specific
        replica. E.g. A local replica would log the initial write, and remote
        replicas would log the remote access accordingly.
        """
        # Construct the prefix
        prefix  = "retrying " if self.attempts > 1 else ""
        prefix += "remote " if self.is_remote_to(replica) else ""

        # Compute the target of the access predicate
        target  = "version {}".format(self.version) if self.version else None
        target  = target or "object {}".format(self.name)

        # Log the complete message
        message = "{}{} {} on {}".format(prefix, self.type, target, replica)
        self.sim.logger.info(message)

    def __str__(self):
        return "{} {}".format(self.type, self.name)


##########################################################################
## Read and Write Events
##########################################################################

class Read(Access):

    def drop(self, empty=False):
        """
        Measures the following metrics:

            - missed read latency
            - missed reads
            - empty reads (read before write)

        Logs the following information:

            - missed reads
            - empty reads (read before write)
        """
        super(Read, self).drop()

        # Empty reads are a special case of missed reads
        if empty:

            # Count the number of missed reads
            self.sim.results.update(
                'empty reads', (self.owner.id, self.env.now)
            )

            # Log the missed read
            self.sim.logger.info(
                "empty read of object {} on {}".format(self.name, self)
            )

        # Otherwise this is a missed read
        else:

            # Track the drop latency
            self.sim.results.update(
                'missed read latency',
                (self.owner.id, self.name, self.started, self.finished)
            )

            # Count the number of missed reads
            self.sim.results.update(
                'missed reads', (self.owner.id, self.env.now)
            )

            # Log the missed read
            self.sim.logger.info(
                "missed read of object {} on {}".format(self.name, self)
            )

        return self

    def complete(self):
        """
        Measures the following metrics:

            - read latency
            - stale reads

        Logs the following information:

            - stale reads
        """
        super(Read, self).complete()

        # Track the read latency
        self.sim.results.update(
            'read latency',
            (self.owner.id, str(self.version), self.started, self.finished)
        )

        if self.version.is_stale():
            # Count the number of stale reads
            self.sim.results.update(
                'stale reads', (self.owner.id, self.env.now)
            )

            # Log the stale read
            self.sim.logger.info(
                "stale read of version {} on {}".format(self.version, self)
            )

        return self

class Write(Access):

    def drop(self):
        """
        Measures the following metrics:

            - dropped write latency
            - dropped writes

        Logs the following information:

            - dropped writes
        """
        super(Write, self).drop()

        # Track the drop latency
        self.sim.results.update(
            'dropped write latency',
            (self.owner.id, self.name, self.started, self.finished)
        )

        # Count the number of missed reads
        self.sim.results.update(
            'dropped writes', (self.owner.id, self.env.now)
        )

        # Log the missed read
        self.sim.logger.info(
            "dropped write of object {} on {}".format(self.name, self)
        )

        return self

    def update(self, version, completed=False):
        """
        Also associates the access with the version (memory leak prone!)
        """
        super(Write, self).update(version, completed)
        self.version.access = self

        return self

    def complete(self):
        """
        Measures the following metrics:

            - write latency

        Logs the following information:

            -
        """
        super(Write, self).complete()

        # Track the write latency
        self.sim.results.update(
            'write latency',
            (self.owner.id, str(self.version), self.started, self.finished)
        )

        return self
