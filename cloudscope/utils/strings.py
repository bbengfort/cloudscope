# cloudscope.utils.strings
# String handling helper functions.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Apr 05 07:30:11 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: strings.py [] benjamin@bengfort.com $

"""
String handling helper functions.
"""

##########################################################################
## Imports
##########################################################################

import re


##########################################################################
## Helper Functions
##########################################################################

# camelize regular expressions
UCAPRE = re.compile(r'(?:^|_)(\w)')

def camelize(s):
    """
    Takes a string in snake_case and returns CamelCase.
    http://stackoverflow.com/questions/4303492/how-can-i-simplify-this-conversion-from-underscore-to-camelcase-in-python
    """
    return UCAPRE.sub(lambda m: m.group(1).upper(), s)


# decamelize regular expressions
FCAPRE = re.compile(r'(.)([A-Z][a-z]+)')
ACAPRE = re.compile(r'([a-z0-9])([A-Z])')

def decamelize(s):
    """
    Takes a string in CamelCase and returns snake_case.
    http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    """
    s = FCAPRE.sub(r'\1_\2', s)
    s = ACAPRE.sub(r'\1_\2', s)
    return s.lower()


def snake_case(s):
    """
    Converts a string with spaces to snake_case.
    """
    return s.replace(" ", "_").lower()


def title_snaked(text):
    """
    Converts a string in snake_case to Title Case
    """
    return " ".join([t.capitalize() for t in text.split("_")])
