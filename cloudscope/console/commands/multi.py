# console.commands.multi
# Multiprocess runner for running many simulations simultaneously.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Feb 17 19:13:06 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: multi.py [] benjamin@bengfort.com $

"""
Multiprocess runner for running many simulations simultaneously.
"""

##########################################################################
## Imports
##########################################################################

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


##########################################################################
## Command
##########################################################################

def runner(idx, data):
    """
    Takes an open file-like object and runs the simulation, returning a
    string containing the dumped JSON results, which can be dumped to disk.
    """
    logger = logging.getLogger('cloudscope')

    fobj = StringIO(data)
    fobj.seek(0)

    try:
        sim = ConsistencySimulation.load(fobj)
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
        'topology': {
            'nargs': "+",
            'type': argparse.FileType('r'),
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

        # Create a pool of processes and begin to execute experiments
        with Timer() as timer:
            pool    = mp.Pool(processes=args.tasks)
            results = [
                pool.apply_async(runner, args=(i+1,x))
                for i, x in enumerate(experiments)
            ]

            output   = [json.loads(p.get()) for p in results]
            duration = sum([
                result['timer']['finished'] - result['timer']['started']
                for result in output
            ])

        # Dump the output data to a file.
        if args.output is None:
            path = "{}-multi-{}.json".format(
                output[0]['simulation'], int(output[0]['timer']['finished'])
            ).replace(" ", "-").lower()
            args.output = open(path, 'w')
        json.dump(output, args.output)

        return (
            "{} simulations ({} compute time) run by {} tasks in {}\n"
            "Results for {} written to {}"
        ).format(
            len(results), humanizedelta(seconds=duration), args.tasks, timer,
            output[0]['simulation'], args.output.name
        )

    def get_experiments(self, args):
        """
        Converts the topologies into JSON data to serialize across processes.
        """
        for topology in args.topology:
            yield topology.read()
