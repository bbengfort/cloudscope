# cloudscope
# Visualization of distributed systems and communications.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Jan 07 16:09:40 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: __init__.py [] benjamin@bengfort.com $

"""
Visualization of distributed systems and communications.
"""

##########################################################################
## Imports
##########################################################################



##########################################################################
## Module Info
##########################################################################

__version_info__ = {
    'major': 0,
    'minor': 1,
    'micro': 0,
    'releaselevel': 'final',
    'serial': 0,
}


def get_version(short=False):
    """
    Prints the version.
    """
    assert __version_info__['releaselevel'] in ('alpha', 'beta', 'final')
    vers = ["%(major)i.%(minor)i" % __version_info__, ]
    if __version_info__['micro']:
        vers.append(".%(micro)i" % __version_info__)
    if __version_info__['releaselevel'] != 'final' and not short:
        vers.append('%s%i' % (__version_info__['releaselevel'][0],
                              __version_info__['serial']))
    return ''.join(vers)

##########################################################################
## Package Version
##########################################################################

__version__ = get_version()
