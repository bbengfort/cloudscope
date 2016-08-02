# cloudscope.console.commands.traces
# Generates random traces to pass directly to the simulations (as input).
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Mar 10 22:39:58 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: traces.py [] benjamin@bengfort.com $

"""
Generates random traces to pass directly to the simulations (as input).
"""

##########################################################################
## Imports
##########################################################################

import sys
import random
import logging
import argparse

from operator import itemgetter
from collections import defaultdict

from commis import Command
from cloudscope.config import settings
from cloudscope.dynamo import CharacterSequence
from cloudscope.simulation.main import ConsistencySimulation
from cloudscope.simulation.workload import WorkloadAllocation
from cloudscope.simulation.workload.traces import TracesWriter
from cloudscope.simulation.workload.cases import BestCaseAllocation
from cloudscope.simulation.workload.cases import PingPongWorkload

##########################################################################
## Command
##########################################################################

class TracesCommand(Command):

    name = 'traces'
    help = 'generate random access traces to write to disk'
    args = {
        '--best-case': {
            'action': 'store_true',
            'help': 'special manual trace generation: best case scenario',
        },
        '--ping-pong': {
            'action': 'store_true',
            'help': 'special manual trace generation: ping pong scenario',
        },
        '--tiered': {
            'action': 'store_true',
            'help': 'special manual trace generation: tiered quorum scenario',
        },
        ('-u', '--users'): {
            'type': int,
            'default': settings.simulation.users,
            'metavar': 'N',
            'help': 'specify the number of users to trace'
        },
        ('-o', '--objects'): {
            'type': int,
            'default': settings.simulation.max_objects_accessed,
            'metavar': 'N',
            'help': 'specify the number of objects accessed'
        },
        ('-t', '--timesteps'): {
            'type': int,
            'default': settings.simulation.max_sim_time,
            'metavar': 'N',
            'help': 'specify the number of timesteps in the trace'
        },
        ('-w', '--output'): {
            'type': argparse.FileType('w'),
            'default': sys.stdout,
            'metavar': 'PATH',
            'help': 'specify location to write traces to',
        },
        'data': {
            'nargs': '+',
            'type': argparse.FileType('r'),
            'default': None,
            'metavar': 'data.json',
            'help': 'topology to generate access traces for'
        }
    }


    def handle(self, args):
        """
        Uses the multi-object workload to generate a traces file.
        """
        # Disable logging during trace generation
        logger = logging.getLogger('cloudscope.simulation')
        logger.disabled = True

        # Simulation arguments
        kwargs = {
            'users': args.users,
            'objects': args.objects,
            'max_sim_time': args.timesteps,
            'trace': None,
        }

        # Create simulation
        simulation = ConsistencySimulation.load(args.data[0], **kwargs)

        # Create or select the correct simulation
        if args.best_case:
            workload = BestCaseAllocation(
                simulation, args.objects, 'random',
            )
            workload.allocate_many(args.users)

        elif args.ping_pong:
            factory = CharacterSequence(upper=True)
            objects = [factory.next() for _ in range(args.objects)]
            workload = PingPongWorkload(
                simulation, simulation.replicas[:args.users], objects=objects,
            )

        elif args.tiered:
            raise NotImplementedError("Tiered hasn't been refactored")

        else:
            simulation.script()
            workload = simulation.workload

        # Create the traces writer and write the traces to disk
        writer = TracesWriter(workload, args.timesteps)
        rows   = writer.write(args.output)

        return (
            "traced {} accesses on {} objects by {} users over {} timesteps\n"
            "wrote the trace file to {}"
        ).format(
            rows, args.objects, args.users, args.timesteps, args.output.name
        )

    def tiered_trace(self, workload, args):
        """
        Manual trace generation to create a "tiered quorum" scenario where
        accesses to a single tag only occur in a single location, e.g. the
        tag space is divided evenly on a per-replica basis.

        Each item in the workload represents a user. Each user should be
        restricted to their own location, and not allowed to move locations,
        they should also be restricted to their own portion of the tagset.
        """
        sequence  = CharacterSequence(upper=True)
        locations = workload[0].locations.keys()

        # Delete the locations from the workload not assigned.
        # Assign a specific tag space to that workload.
        for idx, work in enumerate(workload):
            loc = idx % len(locations)
            for jdx, key in enumerate(work.locations.keys()):
                if jdx != loc:
                    del work.locations[key]

            work.objects = [sequence.next() for _ in xrange(args.objects)]


        # Write the traces to disk
        for idx, access in enumerate(self.compute_accesses(workload, args.timesteps)):
            args.output.write("\t".join(access) + "\n")

        return (
            "traced {} accesses in {} locations ({} objects per location) by {} users over {} timesteps\n"
            "wrote the trace file to {}"
        ).format(
            idx+1, len(locations), args.objects, args.users, args.timesteps, args.output.name
        )
