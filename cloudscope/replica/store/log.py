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