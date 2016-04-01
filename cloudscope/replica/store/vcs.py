# cloudscope.replica.store.vcs
# Definition of what a replica actually stores and manages (data objects).
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 06:51:09 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: vcs.py [] benjamin@bengfort.com $

"""
Definition of what a replica actually stores and manages (data objects).
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.dynamo import Sequence, CharacterSequence


##########################################################################
## Object Factory
##########################################################################

class ObjectFactory(object):
    """
    Creates a new object class with versioning.
    """

    def __init__(self):
        self.counter = CharacterSequence(upper=True)

    def __call__(self):
        return Version.new(self.counter.next())

factory = ObjectFactory()

##########################################################################
## Version Objects
##########################################################################

class Version(object):
    """
    A representation of a write to an object in the replica; the Version
    tracks all information associated with that write (e.g. the version that
    it was written from, when and how long it took to replicate the write).
    """

    @classmethod
    def new(klass, name):
        """
        Returns a new subclass of the version for a specific object and
        resets the global counter on the object, for multi-version systems.
        """
        name = name or "foo" # Handle passing None into the new method.
        return type(name, (klass,), {"counter": Sequence()})


    # Autoincrementing ID
    counter = Sequence()

    def __init__(self, replica, parent=None, **kwargs):
        """
        Creation of an initial version for the version tree.
        """
        self.writer    = replica
        self.parent    = parent
        self.version   = self.counter.next()
        self.committed = False
        self.tag       = kwargs.get('tag', None)

        # This seems very tightly coupled, should we do something different?
        self.replicas  = set([replica.id])
        self.level     = kwargs.get('level', replica.consistency)

        self.created   = kwargs.get('created', replica.env.now)
        self.updated   = kwargs.get('updated', replica.env.now)

    @property
    def name(self):
        """
        Returns the name if it was created via the new function.
        (e.g. is not `Version`)
        """
        name = self.__class__.__name__
        if name != "Version": return name

    def update(self, replica, commit=False):
        """
        Replicas call this to update on remote writes.
        This method also tracks visibility latency for right now.
        """
        self.updated  = replica.env.now

        if replica.id not in self.replicas:
            self.replicas.add(replica.id)

            # Is this version completely replicated?
            if len(self.replicas) == len(replica.sim.replicas):
                # Track the visibility latency
                self.writer.sim.results.update(
                    'visibility latency',
                    (self.writer.id, str(self), self.created, self.updated)
                )

        if commit and not self.committed:
            self.committed = True
            self.writer.sim.results.update(
                'commit latency',
                (self.writer.id, str(self), self.created, self.updated)
            )

    def is_committed(self):
        """
        Alias for committed.
        """
        return self.committed

    def is_visible(self):
        """
        Compares the set of replicas with the global replica set to determine
        if the version is fully visible on the cluster. (Based on who updates)
        """
        return len(self.replicas) == len(self.writer.sim.replicas)

    def is_stale(self):
        """
        Compares the version of this object to the global counter to determine
        if this vesion is the latest or not.
        """
        return not self.version == self.counter.value

    def fork(self, replica, **kwargs):
        """
        Creates a fork of this version
        """
        return self.__class__(
            replica, parent=self, level=self.level
        )

    def read(self, replica, **kwargs):
        """
        Creates a read event of this version
        """
        return ReadVersion(replica, self, **kwargs)

    def contiguous(self):
        """
        Counts the number of contiguous versions between the parent and this
        version; use this method to detect conflicts between different forks.
        """
        if self.parent:
            # Is the parent one less than this version?
            if self.parent.version == self.version - 1:
                return self.parent.contiguous() + 1
        return -1

    def __str__(self):
        def mkvers(item):
            if item.name:
                return "{}.{}".format(item.name, item.version)
            return item.version

        if self.parent:
            return "{}->{}".format(mkvers(self.parent), mkvers(self))
        return "root->{}".format(mkvers(self))

    def __repr__(self):
        return repr(str(self))

    ## Version comparison methods
    def __lt__(self, other):
        return self.version < other.version

    def __le__(self, other):
        return self.version <= other.version

    def __eq__(self, other):
        if other is None: return False
        if self.version == other.version:
            if self.parent is None:
                return other.parent is None
            return self.parent.version == other.parent.version
        return False

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        return self.version > other.version

    def __ge__(self, other):
        return self.version >= other.version


##########################################################################
## Read Event
##########################################################################

class ReadVersion(object):
    """
    Tracks information about a version read over time - particularly the
    latency of the read if the read is remote or must await a consensus
    decision. This is an event that acts as a closure around a single version.
    """

    def __init__(self, replica, version=None, completed=False, **kwargs):
        """
        Creation of an initial version for the version tree.
        """
        self.reader   = replica
        self.version  = version

        self.started  = kwargs.get('started', replica.env.now)
        self.finished = kwargs.get('finished', None)

        if completed: self.complete()

    @property
    def name(self):
        """
        Returns the version name, or if this simply wraps a string, then that.
        """
        if isinstance(self.version, Version):
            return self.version.name
        return self.version

    def is_completed(self):
        """
        Determines if the read is completed
        """
        return self.version is not None and self.finished is not None

    def update(self, version):
        """
        Update the read with the version to respond to the read with.
        """
        self.version = version

    def complete(self):
        """
        Completes the read allowing latency measurement.
        This method also performs all logging and event measurement.
        """
        self.finished = self.reader.env.now

        # Track the read latency
        self.reader.sim.results.update(
            'read latency',
            (self.reader.id, str(self.version), self.started, self.finished)
        )

        if self.is_stale():
            # Count the number of stale reads
            self.reader.sim.results.update(
                'stale reads', (self.reader.id, self.reader.env.now)
            )

    def delay(self):
        """
        Returns the read latency
        """
        if self.is_completed:
            return self.finished - self.started

    def is_stale(self):
        """
        Determines if the read is stale or not.
        """
        return self.version.is_stale()

    def __str__(self):
        return repr(self.name)
