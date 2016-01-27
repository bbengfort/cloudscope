# cloudscope.console.commands.viz
# Console utility to generate visualizations.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 20:09:46 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: viz.py [] benjamin@bengfort.com $

"""
Console utility to generate visualizations.
"""

##########################################################################
## Imports
##########################################################################

import argparse

from commis import Command
from cloudscope.results import Results


##########################################################################
## Command
##########################################################################

class VisualizeCommand(Command):

    name = 'visualize'
    help = 'create visualizations from a results file.'
    args = {
        ('-s', '--savefig'): {
            'type': str,
            'default': None,
            'metavar': 'name.svg',
            'help': 'specify location to save the figure to',
        },
        ('-t', '--type'): {
            'type': str,
            'default': 'workload',
            'choices': ('workload',),
            'help': 'specify the type of visualization',
        },
        'results': {
            'nargs': 1,
            'type': argparse.FileType('r'),
            'default': None,
            'metavar': 'results.json',
            'help': 'results data file to load'
        }
    }

    def handle(self, args):
        results = Results.load(args.results[0])
        if args.savefig:
            results.plot_workload(savefig=args.savefig)
            return ""

        plt = results.plot_workload()
        plt.show()
