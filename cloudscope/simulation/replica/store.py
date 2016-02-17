# cloudscope.simulation.replica.store
# Definition of what a replica actually stores and manages (data objects).
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 06:51:09 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: store.py [] benjamin@bengfort.com $

"""
Definition of what a replica actually stores and manages (data objects).
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.dynamo import Sequence

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

        # This seems very tightly coupled, should we do something different?
        self.level    = kwargs.get('level', replica.consistency)
        self.created  = kwargs.get('created', replica.env.now)
        self.updated  = kwargs.get('updated', replica.env.now)

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
        return Version(
            replica, parent=self, level=self.level, created=self.created
        )

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
        if self.parent:
            return "{}->{}".format(self.parent.version, self.version)
        return "root->{}".format(self.version)

    def __repr__(self):
        return repr(str(self))

    ## Version comparison methods
    def __lt__(self, other):
        return self.version < other.version

    def __le__(self, other):
        return self.version <= other.version

    def __eq__(self, other):
        return self.version == other.version and self.parent == other.parent

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        return self.version > other.version

    def __ge__(self, other):
        return self.version >= other.version
