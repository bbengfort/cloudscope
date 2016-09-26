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

from cloudscope.replica.access import Write
from cloudscope.dynamo import Sequence, CharacterSequence
from cloudscope.exceptions import WorkloadException


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
        self.children  = []
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

    @property
    def access(self):
        """
        Can reconstruct an access given the information in the version, or
        the API allows the use of the setter to assign the Write access that
        created the version for storage and future use.
        """
        if not hasattr(self, '_access'):
            self._access = Write(
                self.name, self.writer, version=self,
                started=self.created, finished=self.updated
            )
        return self._access

    @access.setter
    def access(self, access):
        """
        Assign a Write event that created this particular version for use in
        passing the event along in the distributed system.
        """
        self._access = access

    def update(self, replica, commit=False):
        """
        Replicas call this to update on remote writes.
        This method also tracks visibility latency for right now.
        """
        self.updated  = replica.env.now

        if replica.id not in self.replicas:
            self.replicas.add(replica.id)

            # Track replication over time
            visibility = float(len(self.replicas)) / float(len(replica.sim.replicas))
            self.writer.sim.results.update(
                'visibility',
                (self.writer.id, str(self), visibility, self.created, self.updated)
            )

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

    def is_forked(self):
        """
        Detect if we have multiple children or not. This is a "magic" method
        of determining if the fork exists or not ... for now. We need to make
        this "non-magic" soon.
        """
        # TODO: Non-magic version of this
        # Right now we are computing how many un-dropped children exist
        dropped = lambda child: not child.access.is_dropped()
        return len(filter(dropped, self.children)) > 1

    def nextv(self, replica, **kwargs):
        """
        Returns a clone of this version, incremented to the next version.
        """
        # TODO: ADD THIS BACK IN!
        # Do not allow dropped writes to be incremented
        # if self.access.is_dropped():
        #     msg = (
        #         "Cannot write to a dropped version! "
        #         "{} {} attempting to write {}"
        #     ).format(self.writer.__class__.__name__, self.writer, self)
        #     raise WorkloadException(msg)

        # Detect if we're a stale write (e.g. the parent version is stale).
        # NOTE: You have to do this before you create the next version
        # otherwise by definition the parent is stale!
        if self.is_stale():
            # Count the number of stale writes as well as provide a mechanism
            # for computing time and version staleness for the write.
            self.writer.sim.results.update(
                'stale writes', (
                    self.writer.id,
                    self.writer.env.now, self.created,
                    self.counter.value, self.version,
                )
            )

        # Create the next version at this point.
        nv = self.__class__(
            replica, parent=self, level=self.level
        )

        # Append the next version to your children
        self.children.append(nv)

        # Detect if we've forked the write
        if self.is_forked():
            # Count the number of forked writes
            self.writer.sim.results.update(
                'forked writes', (self.writer.id, self.writer.env.now)
            )

        return nv

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
