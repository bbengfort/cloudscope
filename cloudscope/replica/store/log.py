# cloudscope.replica.conensus.log
# Implements a "write-ahead" log for Raft storage.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Feb 19 10:38:08 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: log.py [] benjamin@bengfort.com $

"""
Implements a "write-ahead" log for Raft storage.
"""

##########################################################################
## Imports
##########################################################################

from collections import namedtuple


##########################################################################
## Data Structures
##########################################################################

LogEntry  = namedtuple("LogEntry", "version, term")
NullEntry = LogEntry(None, 0)

##########################################################################
## Write Log
##########################################################################

class WriteLog(object):
    """
    A wrapper around a simple list that provides added log functionality.
    """

    def __init__(self):
        # Log is initialized with null value at index 0
        # Log stores (version, term) tuples.
        self.log = [NullEntry]

        # index of highest log entry applied
        self.lastApplied = 0

        # index of highest log entry known to be committed
        self.commitIndex = 0

    @property
    def lastTerm(self):
        """
        Returns the last term applied to the log.
        """
        return self[-1].term

    @property
    def lastVersion(self):
        """
        Returns the last version applied to the log.
        """
        return self[-1].version

    @property
    def lastCommit(self):
        """
        Returns the last version committed to the log.
        """
        return self.log[self.commitIndex].version

    def insert(self,index, version, term):
        """
        Inserts a version at the specified index and increments last Applied.
        Technically, we really shouldn't be inserting anything into logs!
        """
        self.log.insert(index, LogEntry(version, term))
        self.lastApplied += 1

    def append(self, version, term):
        """
        Appends a version and a term to the log.
        """
        self.log.append(LogEntry(version, term))
        self.lastApplied += 1

    def remove(self, after=1):
        """
        Removes all items from a log after the specified index.
        """
        self.log = self.log[:after]
        self.lastApplied = len(self.log) - 1

    def as_up_to_date(self, lastTerm, lastApplied):
        """
        Returns True if the log specified by its last term and last applied is
        at least as up to date (or farther ahead) than this log.
        """
        if self.lastTerm == lastTerm:
            return lastApplied >= self.lastApplied
        return lastTerm > self.lastTerm

    def freeze(self):
        """
        Returns an immutable copy of the log.
        """
        return tuple(self.log)

    def __getitem__(self, idx):
        return self.log[idx]

    def __iter__(self):
        for item in self.log:
            yield item

    def __len__(self):
        return len(self.log)

    def __gt__(self, other):
        """
        Returns true if self is "more up to date" than other.
        """
        if self.lastTerm == other.lastTerm:
            return self.lastApplied > other.lastApplied
        return self.lastTerm > other.lastTerm

    def __ge__(self, other):
        """
        Returns true if self is "as up to date or more up to date" than other.
        """
        if self.lastTerm == other.lastTerm:
            return self.lastApplied >= other.lastApplied
        return self.lastTerm >= other.lastTerm

    def __eq__(self, other):
        """
        Returns true if the last term of both logs is the same, and they have
        logs of the same length (e.g. compare lastTerm and lastApplied).

        The semantics reads: "are as up to date as each other"
        """
        if self.lastTerm == other.lastTerm:
            if self.lastApplied == other.lastApplied:
                return True
        return False

    def __ne__(self, other):
        return not self == other

    def __le__(self, other):
        """
        Returns true if self is "as up to date or less up to date" than other.
        """
        if self.lastTerm == other.lastTerm:
            return self.lastApplied <= other.lastApplied
        return self.lastTerm <= other.lastTerm

    def __lt__(self, other):
        """
        Returns true if self is "less up to date" than other.
        """
        if self.lastTerm == other.lastTerm:
            return self.lastApplied < other.lastApplied
        return self.lastTerm < other.lastTerm


##########################################################################
## Multi Object Write Log
##########################################################################

class MultiObjectWriteLog(WriteLog):
    """
    Provides added functionality for a single log that can store an entire
    namespace of objects (not efficient, but practical).
    """

    def __init__(self, *args, **kwargs):
        super(MultiObjectWriteLog, self).__init__(*args, **kwargs)

        # Keep track of the object namespace
        self.namespace = set()

    def append(self, version, term):
        """
        Appends a version and a term to the log.
        """
        self.namespace.add(version.name)
        super(MultiObjectWriteLog, self).append(version, term)

    def insert_before(self, ancestor, version, term):
        """
        Inserts the version and term to the log before the ancestor, which is
        searched for from the reverse of the list.
        """
        for idx in xrange(self.lastApplied, -1, -1):
            # Note that we have to use is for identity checking.
            if self[idx].version is ancestor:
                self.insert(idx, version, term)
                break

    def search(self, name, start=None):
        """
        Searches the log for the name in reverse order.
        """
        # Start from the last applied index, and search backward for the name
        start = start or self.lastApplied
        for idx in xrange(start, -1, -1):
            entry = self[idx]
            if entry.version is not None and entry.version.name == name:
                return entry

        # Return the null object if search comes up empty
        return self[0]

    def since(self, version, start=None):
        """
        Returns all versions for that name since the specified version.
        """
        start = start or self.lastApplied
        for idx in xrange(start, -1, -1):
            entry = self[idx]
            if entry.version is version:
                return [
                    entry.version for entry in self.log[idx+1:]
                    if entry.version.name == version.name
                ]

        # Didn't find anything so return empty list
        return []

    def get_latest_version(self, name):
        """
        Get the latest version for the name given.
        """
        entry = self.search(name)
        return entry.version

    def get_latest_commit(self, name):
        """
        Get the latest name for the commit given.
        """
        entry = self.search(name, self.commitIndex)
        return entry.version

    def items(self, committed=True):
        """
        Returns an iterable of object names and their latest commit versions
        unless committed is False, then returns their latest versions.
        """
        for name in self.namespace:
            if committed:
                yield name, self.get_latest_commit(name)
            else:
                yield name, self.get_latest_version(name)
