# cloudscope.utils.serialize
# Provides helpers for JSON serialization to disk.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sun Dec 06 21:37:53 2015 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: serialize.py [d0f0ca1] benjamin@bengfort.com $

"""
Provides helpers for JSON serialization to disk.
"""

##########################################################################
## Imports
##########################################################################

import json
import datetime

JSON_DATETIME = "%Y-%m-%dT%H:%M:%S.%fZ"

##########################################################################
## JSON encoding
##########################################################################

class JSONEncoder(json.JSONEncoder):

    def encode_datetime(self, obj):
        """
        Converts a datetime object into JSON time.
        """
        # Handle timezone aware datetime objects
        if obj.tzinfo is not None and obj.utcoffset() is not None:
            obj = obj.replace(tzinfo=None) - obj.utcoffset()

        return obj.strftime(JSON_DATETIME)

    def encode_ndarray(self, obj):
        """
        Convert np.array to a list object.
        """
        return list(obj)

    def encode_generator(self, obj):
        """
        Converts a generator into a list
        """
        return list(obj)

    def default(self, obj):
        """
        Perform encoding of complex objects.
        """
        try:
            return super(JSONEncoder, self).default(obj)
        except TypeError:
            # If object has a serialize method, return that.
            if hasattr(obj, 'serialize'):
                return obj.serialize()

            # Look for an encoding method on the Encoder
            method = "encode_%s" % obj.__class__.__name__
            if hasattr(self, method):
                method = getattr(self, method)
                return method(obj)

            # Not sure what is going on if the above two methods didn't work
            raise TypeError(
                "Could not encode type '{0}' using {1}\n"
                "Either add a serialze method to the object, or add an "
                "encode_{0} method to {1}".format(
                    obj.__class__.__name__, self.__class__.__name__
                )
            )
