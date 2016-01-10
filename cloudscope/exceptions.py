# cloudscope.exceptions
# Exceptions hierarchy for cloudscope
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sat Jan 09 17:00:25 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: exceptions.py [] benjamin@bengfort.com $

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