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

from cloudscope.config import settings
from cloudscope.replica.access import Write
from cloudscope.replica import State, Consistency
from cloudscope.dynamo import Sequence, CharacterSequence
from cloudscope.exceptions import WorkloadException, ImproperlyConfigured
from cloudscope.exceptions import SimulationException

from collections import defaultdict, namedtuple


##########################################################################
## Namespace and Object Factory
##########################################################################

class Namespace(object):
    """
    Creates and manages all object classes in the namespace.
    """

    def __init__(self):
        self.names = {}

    def reset(self):
        """
        Resets the namespace.
        """
        for key in self.names.keys():
            del self.names[key]

    def get_version_class(self):
        """
        Returns the class type for the version.
        """
        klass = {
            'default': Version,
            'lamport': LamportVersion,
            'federated': FederatedVersion,
        }.get(settings.simulation.versioning, None)

        if klass is None:
            raise ImproperlyConfigured(
                "'{}' is not a valid versioning method.".format(
                    settings.simulation.versioning
                )
            )

        return klass

    def __call__(self, name):
        if name not in self.names:
            klass = self.get_version_class()
            self.names[name] = klass.new(name)
        return self.names[name]


## The initialized namespace
namespace = Namespace()


class ObjectFactory(object):
    """
    Creates a new object class with versioning.
    """

    def __init__(self, namespace=None):
        self.namespace = namespace or Namespace()
        self.counter   = CharacterSequence(upper=True)

    def __call__(self):
        return self.namespace(self.counter.next())

    def reset(self):
        """
        Resets the namespace
        """
        self.namespace.reset()


## The initialized object factory
factory = ObjectFactory(namespace)


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

    @classmethod
    def increment_version(klass, replica):
        """
        Returns the next unique version number in the global sequence.
        This method takes as input the replica writing the version number so
        that subclasses can implement replica-specific versioning.
        """
        return klass.counter.next()

    @classmethod
    def latest_version(klass):
        """
        Returns the latest global version of this object.
        """
        return klass.counter.value


    def __init__(self, replica, parent=None, **kwargs):
        """
        Creation of an initial version for the version tree.
        """
        self.writer    = replica
        self.version   = self.increment_version(replica)
        self.parent    = parent
        self.children  = []
        self.committed = False
        self.tag       = kwargs.get('tag', None)

        # This seems very tightly coupled, should we do something different?
        self.replicas  = set([replica.id])

        # Level is depcrecated and no longer used.
        # TODO: Remove the level cleanly
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

    def update(self, replica, commit=False, **kwargs):
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
        return self.version < self.latest_version()

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
        # The problem is that this is global knowledge and cannot be checked.
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
                    self.latest_version(), self.version,
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
## Lamport Version Objects.
##########################################################################

class LamportScalar(object):
    """
    This is just a simple, comparable data structure. However, it does not
    have to be separate from the LamportVersion class - and should be
    refactored into it.
    """

    # TODO: Refactor this code into the LamportVersion class.

    def __init__(self, replica, version):
        self.replica = replica
        self.version = version

    def __str__(self):
        return "{}.{}".format(self.replica, self.version)

    def __repr__(self):
        return str(self)

    ## Version comparison methods
    def __lt__(self, other):
        # Start with type check
        if type(self) == type(other):
            # If version numbers are equal tie-break with replica.
            if self.version == other.version:
                return self.replica < other.replica

            # Otherwise return the inequality between version numbers
            return self.version < other.version

        # Comparsion to a number
        if isinstance(other, (int, float)):
            return self.version < other

        raise TypeError(
            "Cannot compare '{}' to '{}'".format(
                type(self), type(other)
            )
        )

    def __le__(self, other):
        if self == other: return True
        return self < other

    def __eq__(self, other):
        # Start with type check
        if type(self) == type(other):
            # Compare both replica and the version tuples.
            return (self.replica, self.version) == (other.replica, other.version)

        # Comparsion to a number
        if isinstance(other, (int, float)):
            return self.version == other

        # Otherwise return False
        return False

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        # Start with type check
        if type(self) == type(other):
            # If version numbers are equal tie-break with replica.
            if self.version == other.version:
                return self.replica > other.replica

            # Otherwise return the inequality between version numbers
            return self.version > other.version

        # Comparsion to a number
        if isinstance(other, (int, float)):
            return self.version > other

        raise TypeError(
            "Cannot compare '{}' to '{}'".format(
                type(self), type(other)
            )
        )

    def __ge__(self, other):
        if self == other: return True
        return self > other


class LamportVersion(Version):
    """
    A version class that makes use of Lamport scalar numbers assigned to each
    replica as version numbers, rather than a globally increasing constant.

    Lamport versions are not fully implemented as the Replicas must modify
    their counter sequence with the maximal value they've seen from all
    messages - a task that directly modifies this class from the outside.

    As such, Lamport versions are currently in use.
    """

    # TODO: Fully implement Lamport Versions by having replicas update class.

    @classmethod
    def new(klass, name):
        """
        Returns a new subclass of the version for a specific object and
        resets the global counter on the object, for multi-version systems.
        """
        name = name or "foo" # Handle passing None into the new method.
        return type(name, (klass,), {"counter": defaultdict(Sequence)})

    # Per-Replica auto-incrementing ID
    counter = defaultdict(Sequence)

    @classmethod
    def increment_version(klass, replica):
        """
        Returns the next unique version number in the global sequence.
        This method takes as input the replica writing the version number so
        that subclasses can implement replica-specific versioning.
        """
        return LamportScalar(replica.id, klass.counter[replica.id].next())

    @classmethod
    def latest_version(klass):
        """
        Returns the globally latest version of all versions stored by replicas
        """
        return max([
            counter.value for counter in klass.counter.values()
        ])

    @classmethod
    def update_version(klass, replica, version):
        """
        Updates the version sequence for a given replica from a recently
        received remote version, by setting the counter for that replica
        equal to the maximum between the current value and the version value.
        """
        # Yes, version.version.version is annoying ...
        klass.counter[replica.id].value = max([
            version.version.version, klass.counter[replica.id].value
        ])


##########################################################################
## Federated Version Objects.
##########################################################################

class DualCounter(namedtuple('DualCounter', 'version, forte')):
    """
    Implements a data structure with two counters, one for version numbers
    and the other for Raft's strong consistency counter numbers.
    """

    @classmethod
    def new(klass):
        return klass(Sequence(), Sequence())

    def __str__(self):
        return "version: {} | forte: {}".format(
            self.version.value, self.forte.value
        )


class FederatedVersion(Version):
    """
    A version class that adds additional version information to differentiate
    between Raft serialized version information and Eventual serialized
    versions by adding a secondary counter that only a Raft leader can
    increment and that must be evaluated when comparing versions.
    """

    @classmethod
    def new(klass, name):
        """
        Returns a new subclass of the version for a specific object and
        resets the global counter on the object, for multi-version systems.
        """
        name = name or "foo" # Handle passing None into the new method.
        return type(name, (klass,), {"counter": DualCounter.new()})

    # Autoincrementing ID
    counter = DualCounter.new()

    @classmethod
    def increment_version(klass, replica):
        """
        Returns the next unique version number in the global sequence.
        This method takes as input the replica writing the version number so
        that subclasses can implement replica-specific versioning.
        """
        return klass.counter.version.next()

    @classmethod
    def increment_forte(klass):
        """
        Returns the next unique forte number in the global sequence. Only the
        Raft leader should be allowed to called this method.
        """
        return klass.counter.forte.next()

    @classmethod
    def latest_version(klass):
        """
        Returns the latest global version of this object.
        """
        # TODO: Do we also need to compare against the forte for staleness?
        return klass.counter.version.value

    def __init__(self, replica, parent=None, **kwargs):
        """
        On initialization, also keep track of the forte number - the index
        that keeps track of any committed writes. Only Raft leaders can
        increment the forte number but children inherit the forte number of
        their parents. If there is no parent, the forte number is zero.
        """

        # Set the forte number on the class
        self.forte = parent.forte if parent else 0
        super(FederatedVersion, self).__init__(replica, parent, **kwargs)

    def update(self, replica, commit=False, forte=False, **kwargs):
        """
        The update method allows a Raft leader to now also update the forte
        on this particular instance version. The method does a quick sanity
        check just to make sure only the leader can do this, then happily
        performs the forte update.
        """
        if forte:
            if not replica.consistency in {Consistency.STRONG, Consistency.RAFT}:
                raise SimulationException(
                    "{} attempting to set forte with consistency {}".format(
                        replica, replica.consistency
                    )
                )

            if not replica.state == State.LEADER:
                raise SimulationException(
                    "{} attempting to set forte in state {}".format(
                        replica, replica.state
                    )
                )

            self.forte = self.increment_forte()

        super(FederatedVersion, self).update(replica, commit, **kwargs)

    def __str__(self):
        def mkvers(item):
            vers = "{}.{}".format(item.version, item.forte)
            if item.name:
                vers = "{}.{}".format(item.name, vers)
            return vers

        if self.parent:
            return "{}->{}".format(mkvers(self.parent), mkvers(self))
        return "root->{}".format(mkvers(self))

    ## Version comparison methods
    def __lt__(self, other):
        # Start with type check
        if isinstance(other, FederatedVersion):
            # If forte numbers are equal then compare versions.
            if self.forte == other.forte:
                return self.version < other.version

            # Otherwise return the inequality between forte numbers
            return self.forte < other.forte

        # Comparsion to a number is a direct comparision to the version.
        if isinstance(other, (int, float)):
            return self.version < other

        raise TypeError(
            "Cannot compare '{}' to '{}'".format(
                type(self), type(other)
            )
        )

    def __le__(self, other):
        if self == other: return True
        return self < other

    def __eq__(self, other):
        # Start with type check
        if isinstance(other, FederatedVersion):
            # Compare both replica and the version tuples.
            return (self.version, self.forte) == (other.version, other.forte)

        # Comparsion to a number is a direct comparison to the version.
        if isinstance(other, (int, float)):
            return self.version == other

        # Otherwise return False
        return False

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        # Start with type check
        if isinstance(other, FederatedVersion):
            # If forte numbers are equal then compare versions.
            if self.forte == other.forte:
                return self.version > other.version

            # Otherwise return the inequality between forte numbers
            return self.forte > other.forte

        # Comparsion to a number is a direct comparison to the version.
        if isinstance(other, (int, float)):
            return self.version > other

        raise TypeError(
            "Cannot compare '{}' to '{}'".format(
                type(self), type(other)
            )
        )

    def __ge__(self, other):
        if self == other: return True
        return self > other
