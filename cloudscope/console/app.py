# cloudscope.console.app
# Definition of the Scope app utility and commands.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 14:02:47 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: app.py [123e7af] benjamin@bengfort.com $

"""
Definition of the Scope app utility and commands.
http://bbengfort.github.io/tutorials/2016/01/23/console-utility-commis.html
"""

##########################################################################
## Imports
##########################################################################

from commis import color
from commis import ConsoleProgram
from commis.exceptions import ConsoleError

from cloudscope.version import get_version
from cloudscope.console.commands import *

##########################################################################
## Utility Definition
##########################################################################

DESCRIPTION = "Management and administration commands for CloudScope"
EPILOG      = "If there are any bugs or concerns, submit an issue on Github"
COMMANDS    = [
    ServeCommand,
    SimulateCommand,
    VisualizeCommand,
    MultipleSimulationsCommand,
    GenerateCommand,
    TracesCommand,
    SettingsCommand,
    InspectCommand,
    OutagesCommand,
    ModifyTopologyCommand,
    TopologyGeneratorCommand,
]

##########################################################################
## The CloudScope CLI Utility
##########################################################################

class ScopeUtility(ConsoleProgram):

    description = color.format(DESCRIPTION, color.CYAN)
    epilog      = color.format(EPILOG, color.MAGENTA)
    version     = color.format("scope.py v{}", color.CYAN, get_version())

    @classmethod
    def load(klass, commands=COMMANDS):
        utility = klass()
        for command in commands:
            utility.register(command)
        return utility
