# cloudscope.console.commands.simulate
# Runs the CloudScope simulation with the configuration.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 14:37:05 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: simulate.py [123e7af] benjamin@bengfort.com $

"""
Runs the CloudScope simulation with the configuration.
"""

##########################################################################
## Imports
##########################################################################

import json
import argparse

from datetime import date
from cStringIO import StringIO

from commis import Command
from cloudscope.config import settings
from cloudscope.utils.decorators import Timer
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
            'nargs': '+',
            'type': argparse.FileType('r'),
            'default': None,
            'metavar': 'data.json',
            'help': 'simulation description file to load'
        }
    }

    def get_output_path(self, name="results", today=None, dtfmt="%Y%m%d"):
        """
        Computes an output path based on the current date and name.
        """
        today = date.today() if today is None else today
        today = today.strftime(dtfmt)
        path  = "{}-{}.json".format(name, today)
        path  =  path.replace(" ", "-").lower()

        return open(path, 'w')

    def handle(self, args):
        """
        Entry point for the simulation runner.
        """
        if len(args.data) > 1:
            return self.handle_multiple(args)
        return self.handle_single(args)

    def handle_single(self, args):
        """
        Most common use case for the simulation runner: simply runs a single
        simulation, loading it from the data file.
        """
        sim = ConsistencySimulation.load(args.data[0])
        sim.run()

        # Dump the output data to a file.
        if args.output is None:
            args.output = self.get_output_path(sim.name, sim.results.finished)
        sim.results.dump(args.output)

        # Dump the graph data to a file.
        if args.graph:
            sim.dump(args.graph, indent=2)

        return "Results for {} written to {}".format(sim.name, args.output.name)

    def handle_multiple(self, args):
        """
        Sequentially run multiple simulations. Note the multiprocess command
        is much faster. Only use this command if you have time!
        """
        with Timer() as timer:

            sims   = [
                ConsistencySimulation.load(fobj)
                for fobj in args.data
            ]
            output = [StringIO() for sim in sims]

            for idx, sim in enumerate(sims):
                sim.logger.info("Starting simulation loaded from {!r}".format(args.data[idx].name))
                sim.run()
                sim.results.dump(output[idx])

            output = [json.loads(o.getvalue()) for o in output]

            duration = sum([
                result['timer']['finished'] - result['timer']['started']
                for result in output
            ])

            # Dump the output data to a file.
            if args.output is None:
                args.output = self.get_output_path(sims[0].name + "-multi")
            json.dump(output, args.output)

        return (
            "{} simulations ({} seconds) run in {}\n"
            "Results for {} written to {}"
        ).format(
            len(sims), duration, timer,
            output[0]['simulation'], args.output.name
        )
