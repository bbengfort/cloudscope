# cloudscope.replica.consensus
# Implements strong consistency using consensus protocols.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Feb 19 09:47:53 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [] benjamin@bengfort.com $

"""
Implements strong consistency using consensus protocols.
"""

##########################################################################
## Imports
##########################################################################

from .raft import RaftReplica
from .tag import TagReplica
from .float import FloatedRaftReplica
from .tiered import TieredRaftReplica
