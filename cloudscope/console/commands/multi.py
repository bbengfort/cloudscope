# console.commands.multi
# Multiprocess runner for running many simulations simultaneously.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Feb 17 19:13:06 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: multi.py [3b32635] benjamin@bengfort.com $

"""
Multiprocess runner for running many simulations simultaneously.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import logging
import argparse
import multiprocessing as mp

from commis import Command
from cStringIO import StringIO
from cloudscope.config import settings
from cloudscope.utils.decorators import Timer
from cloudscope.utils.timez import humanizedelta
from cloudscope.simulation.main import ConsistencySimulation
from commis.exceptions import ConsoleError
from collections import Counter

##########################################################################
## Command
##########################################################################

def runner(idx, path, **kwargs):
    """
    Takes an open file-like object and runs the simulation, returning a
    string containing the dumped JSON results, which can be dumped to disk.
    """
    logger = logging.getLogger('cloudscope')

    try:
        with open(path, 'r') as fobj:
            sim = ConsistencySimulation.load(fobj, **kwargs)

        logger.info(
            "Starting simulation {}: \"{}\"".format(idx, sim.name)
        )
        sim.run()

        # Dump the output data to a file.
        output = StringIO()
        sim.results.dump(output)

        # Report completion back to the command line
        logger.info(
            "Simulation {}: \"{}\" completed in {}".format(idx, sim.name, sim.results.timer)
        )

        # Return the string value of the JSON results.
        return output.getvalue()
    except Exception as e:
        logger.error(str(e))

        import traceback, sys
        return json.dumps({
            'success': False,
            'traceback': "".join(traceback.format_exception(*sys.exc_info())),
            'error': str(e),
        })


class MultipleSimulationsCommand(Command):

    name = 'multisim'
    help = 'run multiple simulations with a varying network.'
    args = {
        ('-o', '--output'): {
            'type': argparse.FileType('w'),
            'default': None,
            'metavar': 'DST',
            'help': 'specify location to write output to',
        },
        ('-t', '--tasks'): {
            'type': int,
            'metavar': 'NUM',
            'default': mp.cpu_count(),
            'help': 'number of concurrent simulation task to run',
        },
        ('-T', '--trace'): {
            'type': str,
            'default': None,
            'metavar': 'PATH',
            'help': 'specify the path to the trace file with accesses',
        },
        # Note: can't use argparse.FileType('r') here because of too many open files error!
        'topology': {
            'nargs': "+",
            'type': str,
            'default': None,
            'metavar': 'topology.json',
            'help': 'simulation description file to load'
        }
    }

    def handle(self, args):
        """
        Handles the multiprocess execution of the simulations.
        """
        # Disable Logging During Multiprocess
        logger = logging.getLogger('cloudscope.simulation')
        logger.disabled = True

        # TODO: Change the below to just accept multiple topologies
        experiments = self.get_experiments(args)
        kwargs = {
            'trace': args.trace,
        }

        # Create a pool of processes and begin to execute experiments
        with Timer() as timer:
            pool    = mp.Pool(processes=args.tasks)
            results = [
                pool.apply_async(runner, (i+1,x), kwargs)
                for i, x in enumerate(experiments)
            ]

            # Compute output and errors
            output   = [json.loads(p.get()) for p in results]
            errors   = filter(lambda d: 'error' in d, output)
            output   = filter(lambda d: 'error' not in d, output)

            # Compute duration
            duration = sum([
                result['timer']['finished'] - result['timer']['started']
                for result in output
            ])

            # Compute the most common simulation name
            names = Counter(d['simulation'] for d in output)
            simulation = names.most_common(1)
            simulation = simulation[0][0] if simulation else "(No Simulation Completed)"

        # Dump the output data to a file.
        if args.output is None:
            path = "{}-multi-{}.json".format(
                output[0]['simulation'], int(output[0]['timer']['finished'])
            ).replace(" ", "-").lower()
            args.output = open(path, 'w')
        json.dump(output, args.output)

        return (
            "{} simulations ({} compute time, {} errors) run by {} tasks in {}\n"
            "Results for {} written to {}"
        ).format(
            len(results), humanizedelta(seconds=duration) or "0 seconds",
            len(errors), args.tasks, timer, simulation, args.output.name
        )

    def get_experiments(self, args):
        """
        Converts the topologies into JSON data to serialize across processes.
        """
        for topology in args.topology:
            path = os.path.abspath(topology)

            if not os.path.exists(path) or not os.path.isfile(path):
                raise ConsoleError(
                    "Could not find topology file at '{}'".format(topology)
                )

            yield path
