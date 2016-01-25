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
from cloudscope.simulation.cars import GasStationSimulation


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
        }
    }

    def handle(self, args):
        sim = GasStationSimulation()
        sim.run()

        # Dump the output data to a file.
        if args.output is None:
            path = "{}-{}.json".format(sim.name, sim.results.finished.strftime('%Y%m%d'))
            args.output = open(path, 'w')
        sim.results.dump(args.output)

        return "Results for {} written to {}".format(sim.name, args.output.name)
