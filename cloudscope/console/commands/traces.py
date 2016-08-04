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
import logging
import argparse

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
        Uses built in workloads and the TracesWriter to generate a trace file.
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
        if args.best_case or args.tiered:
            workload = BestCaseAllocation(
                simulation, args.objects, selection='random',
            )
            workload.allocate_many(args.users)

        elif args.ping_pong:
            factory = CharacterSequence(upper=True)
            objects = [factory.next() for _ in range(args.objects)]
            workload = PingPongWorkload(
                simulation, simulation.replicas[:args.users], objects=objects,
            )

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
