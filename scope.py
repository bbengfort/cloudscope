#!/usr/bin/env python
# scope
# Management and administration script for CloudScope
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sat Jan 09 10:03:40 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: scope.py [26b95c0] benjamin@bengfort.com $

"""
Management and administration script for CloudScope
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.console import ScopeUtility

##########################################################################
## Load and execute the CLI utility
##########################################################################

if __name__ == '__main__':
    app = ScopeUtility.load()
    app.execute()
