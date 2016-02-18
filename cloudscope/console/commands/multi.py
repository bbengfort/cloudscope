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

import logging
import argparse
import multiprocessing as mp

from commis import Command
from cloudscope.config import settings
from cloudscope.utils.decorators import Timer
from cloudscope.simulation.main import ConsistencySimulation

# TODO: Remove below
import json
import networkx as nx
from cStringIO import StringIO

##########################################################################
## Command
##########################################################################

def runner(data):
    """
    Takes an open file-like object and runs the simulation, returning a
    string containing the dumped JSON results, which can be dumped to disk.
    """
    logger = logging.getLogger('cloudscope')

    fobj = StringIO(data)
    fobj.seek(0)

    sim = ConsistencySimulation.load(fobj)
    sim.run()

    # Dump the output data to a file.
    output = StringIO()
    sim.results.dump(output)

    # Report completion back to the comamnd line
    logger.info(
        "{!r} simulation completed in {}".format(sim.name, sim.results.timer)
    )

    # Return the string value of the JSON results.
    return output.getvalue()


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
        '--crazy': {
            'action': 'store_true',
            'default': False,
            'help': 'rerun lots of experiments with variations',
        },
        ('-n', '--count'): {
            'type': int,
            'metavar': 'NUM',
            'required': True,
            'help': 'total number of simulations to run'
        },
        'topology': {
            'nargs': 1,
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
                pool.apply_async(runner, args=(x,)) for x in experiments
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
            "{} simulations ({} seconds) run by {} tasks in {}\n"
            "Results for {} written to {}"
        ).format(
            len(experiments), duration, args.tasks, timer,
            output[0]['simulation'], args.output.name
        )

    def get_experiments(self, args):
        if args.crazy:
            import random
            from itertools import chain

            def inner(args):
                args.topology[0].seek(0)
                yield [
                    experiment for experiment in
                    generate_latency_variation_experiment(
                        args.topology[0], args.count,
                        random.randint(5, 100), random.randint(2000, 5000), random.randint(100, 1800)
                )]

            return list(chain(*
                chain(*[
                    list(inner(args))
                    for x in xrange(args.count)
                ])
            ))

        return [
            experiment for experiment in
            generate_latency_variation_experiment(args.topology[0], args.count)
        ]


##########################################################################
## Helper Functions
##########################################################################

def spread(n, start, stop, width=None):
    """
    Given n slices, divide the range between start and stop; factored by
    width. E.g. if width is not given, just give the even n splits.

    If width is given, spread n width wide ranges over the start/stop with
    overlap or gaps depending on how n width wide ranges fits between.
    """

    if width is None:
        width = stop / n

    gap = (stop / n) - width

    for idx in xrange(n):
        yield [start, start + width]
        start += width + gap

def generate_latency_variation_experiment(fobj, n, min_latency=5, max_latency=6000, max_range=1200, max_users=6, user_step=2):
    """
    Reads a topology from a JSON file and creates n experimental files with
    a variation in the minimum and maximum latency across all connections.
    """
    # TODO: This is just a stub, replace soon with better code!
    data  = json.load(fobj)
    width = min(max_range, max_latency / n)

    for users in xrange(1, max_users+1, user_step):
        for latency in spread(n, min_latency, max_latency, width):
            mean_latency = int(sum(map(float, latency)) / len(latency))

            for link in data['links']:
                if link['connection'] == 'variable':
                    link['latency'] = latency
                else:
                    link['latency'] = mean_latency

            data['meta']['users'] = users

            yield json.dumps(data, fobj)
