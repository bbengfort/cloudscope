# cloudscope.replica.federated
# Replicas that implement federated consistency rather than homogenous.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jun 15 22:03:21 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [] benjamin@bengfort.com $

"""
Replicas that implement federated consistency rather than homogenous.
"""

##########################################################################
## Imports
##########################################################################

from .eventual import StentorEventualReplica
from .eventual import FederatedEventualReplica
from .sequential import FederatedRaftReplica
