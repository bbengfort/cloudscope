# cloudscope.replica.consensus.tiered
# Implements strong consistency across a wide area using tiered Raft.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Feb 04 06:57:45 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: tiered.py [] benjamin@bengfort.com $

"""
Implements strong consistency across a wide area using tiered Raft consensus.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.simulation.timer import Timer
from cloudscope.replica.store import Version
from cloudscope.replica import Consistency, State
from cloudscope.exceptions import RaftRPCException, SimulationException
from cloudscope.replica.store import MultiObjectWriteLog

from .raft import RaftReplica

##########################################################################
## Module Constants
##########################################################################

## Timers and timing
GLOBAL_HEARTBEAT_INTERVAL = settings.simulation.heartbeat_interval
GLOBAL_ELECTION_TIMEOUT   = settings.simulation.election_timeout
LOCAL_HEARTBEAT_INTERVAL  = 40
LOCAL_ELECTION_TIMEOUT    = [80,160]

##########################################################################
## Raft Replica
##########################################################################

class TieredRaftReplica(RaftReplica):
    pass
