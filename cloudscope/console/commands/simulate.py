# cloudscope.console.commands.simulate
# Runs the CloudScope simulation with the configuration.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 14:37:05 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: simulate.py [] benjamin@bengfort.com $

"""
Runs the CloudScope simulation with the configuration.
"""

##########################################################################
## Imports
##########################################################################

import argparse

from commis import Command
from cloudscope.config import settings
from cloudscope.simulation.main import ConsistencySimulation


##########################################################################
## Command
##########################################################################

class SimulateCommand(Command):

    name = 'simulate'
    help = 'run the simulation with the given configuration.'
    args = {
        ('-o', '--output'): {
            'type': argparse.FileType('w'),
            'default': None,
            'metavar': 'PATH',
            'help': 'specify location to write output to',
        },
        ('-g', '--graph'): {
            'type': argparse.FileType('w'),
            'default': None,
            'metavar': 'PATH',
            'help': 'specify location to write the simulation graph',
        },
        'data': {
            'nargs': '?',
            'type': argparse.FileType('r'),
            'default': None,
            'metavar': 'data.json',
            'help': 'simulation description file to load'
        }
    }

    def handle(self, args):
        sim = ConsistencySimulation.load(args.data)
        sim.run()

        # Dump the output data to a file.
        if args.output is None:
            path = "{}-{}.json".format(sim.name, sim.results.finished.strftime('%Y%m%d'))
            args.output = open(path, 'w')
        sim.results.dump(args.output)

        # Dump the graph data to a file.
        if args.graph:
            sim.dump(args.graph, indent=2)

        return "Results for {} written to {}".format(sim.name, args.output.name)
