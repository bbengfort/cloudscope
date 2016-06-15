# cloudscope.utils.enums
# Advanced enumeration functionality used in Cloudscope.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Apr 01 14:14:55 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: enums.py [] benjamin@bengfort.com $

"""
Advanced enumeration functionality used in Cloudscope.
"""

##########################################################################
## Imports
##########################################################################

from enum import Enum as PyEnum
from cloudscope.exceptions import UnknownType

##########################################################################
## Advanced Enumeration Functionality
##########################################################################

class Enum(PyEnum):
    """
    This special enumeration class provides some helpful utilities for
    managing enumeration constants specifically for Cloudscope. Primarily it
    does this by providing access to the members in a more meaningful way and
    allows easy serialization and deserialization via the name.
    """

    @classmethod
    def get(cls, name):
        """
        Case insensitive lookup of a name (tries name, upper, lower)
        """
        # Passing in members to the get function should be handled.
        if isinstance(name, cls):
            return name

        # Three types of case sensitivity
        for key in (name, name.upper(), name.lower(), name.title()):
            try:
                return cls[key]
            except KeyError:
                continue

        raise UnknownType(
            "The name {} is not a known type of {}".format(
                name, cls.__name__
            )
        )

    @classmethod
    def aliases(cls):
        """
        Returns all the aliases of the enumeration (usually excluded).
        """
        return [
            member for name, member in cls.__members__.items()
            if member.name != name
        ]

    def describe(self):
        return self.name, self.value

    def serialize(self):
        return self.name.lower()
