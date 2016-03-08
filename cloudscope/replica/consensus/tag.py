# cloudscope.replica.consensus.tag
# Package that implements tag based consensus consistency.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Mar 08 14:28:05 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: tag.py [] benjamin@bengfort.com $

"""
Package that implements tag based consensus consistency.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.replica import Replica, Consistency


##########################################################################
## Tag Replica
##########################################################################

class TagReplica(Replica):

    def read(self, version=None):
        """
        Tag Read
        """

        self.sim.results.update(
            "tag read", (self.id, version.name, self.env.now)
        )

        self.sim.logger.info(
            "tag read of version {} on {}".format(version, self)
        )

    def write(self, version=None):
        """
        Tag Write
        """
        version = version.fork(self)

        self.sim.results.update(
            "tag write", (self.id, version.name, self.env.now)
        )

        self.sim.logger.info(
            "tag write of version {} on {}".format(version, self)
        )
