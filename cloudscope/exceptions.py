# cloudscope.exceptions
# Exceptions hierarchy for cloudscope
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sat Jan 09 17:00:25 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: exceptions.py [9c488d4] benjamin@bengfort.com $

"""
Exceptions hierarchy for cloudscope
"""

##########################################################################
## Exceptions
##########################################################################

class CloudScopeException(Exception):
    """
    Base exception for cloudscope errors.
    """
    pass


class ImproperlyConfigured(CloudScopeException):
    """
    Errors in the configuration of CloudScope.
    """
    pass


class ServerError(CloudScopeException):
    """
    Errors in the development debug server.
    """
    pass


class UnknownType(CloudScopeException):
    """
    An unknown type was passed causing a TypeError of some kind.
    """
    pass


class BadValue(CloudScopeException, ValueError):
    """
    CloudScope specific value error
    """
    pass


class CannotGenerateExperiments(CloudScopeException):
    """
    Errors during the experiment generation process.
    """
    pass


class NotifyError(CloudScopeException):
    """
    Could not send a CloudScope notification via email. 
    """
    pass


##########################################################################
## Simulation Exception Hierarchy
##########################################################################

class SimulationException(CloudScopeException):
    """
    Something went wrong in a simulation.
    """
    pass


class NetworkError(SimulationException):
    """
    Could not send or receive a message between two nodes.
    """
    pass


class WorkloadException(SimulationException):
    """
    Something went wrong in the workload generation.
    """
    pass


class AccessError(SimulationException):
    """
    Something went wrong with an access event (read or write).
    """
    pass


class RaftRPCException(SimulationException):
    """
    Something went wrong in the Raft RPC scheme.
    """
    pass


class TagRPCException(SimulationException):
    """
    Something went wrong in the Tag Consensus RPC scheme.
    """
    pass
