# cloudscope.console.commands.config
# Displays information about the configuration being used.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Apr 06 14:49:31 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: config.py [7009664] benjamin@bengfort.com $

"""
Displays information about the configuration being used.
"""

##########################################################################
## Imports
##########################################################################

from commis import Command
from confire import Configuration
from cloudscope.config import settings
from tabulate import tabulate
from operator import itemgetter

##########################################################################
## Command
##########################################################################

CONFIGS = [
    name for name, conf in settings.options()
    if isinstance(conf, Configuration)
]

##########################################################################
## Command
##########################################################################

class SettingsCommand(Command):
    pass
    name = 'config'
    help = 'display information about the current configuration'
    args = {
        ('-D', '--diff'): {
            'action': 'store_true',
            'help': 'show only the differences to default config.'
        },
        'config': {
            'nargs': '?',
            'choices': CONFIGS,
            'default': 'simulation',
            'help': 'specify the configuration to view in detail.'
        }
    }

    def handle(self, args):
        """
        Prints out the configuration in detail, and even diffs.
        """
        config = getattr(settings, args.config)
        header = ("Option", "Value", "Default") if args.diff else ("Option", "Value")
        table  = [header,]

        for opt, val in sorted(config.options(), key=itemgetter(0)):
            dft = config.__class__.__dict__[opt]
            if args.diff:
                if val == dft:
                    continue

            if isinstance(val, Configuration):
                val = val.__class__.__name__

            if isinstance(val, list):
                val = ", ".join([str(v) for v in val])
                dft = ", ".join([str(v) for v in dft])

            if args.diff:
                table.append((opt, val, dft))
            else:
                table.append((opt, val))

        if len(table) <= 1:
            if args.diff:
                return "The default config is being used with no differences."
            return "No configuration values for {}".format(args.config)

        return tabulate(table, headers="firstrow")
