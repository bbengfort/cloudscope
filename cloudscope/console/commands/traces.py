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
import argparse

from collections import defaultdict

from commis import Command
from cloudscope.config import settings
from cloudscope.simulation.main import ConsistencySimulation
from cloudscope.simulation.workload import Workload
from cloudscope.replica.access import READ, WRITE

##########################################################################
## Command
##########################################################################

class TracesCommand(Command):

    name = 'traces'
    help = 'generate random access traces to write to disk'
    args = {
        '-D': {
            'action': 'store_true',
            'dest': 'debugging',
            'help': 'special manual trace generation',
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
        # Simulation arguments
        kwargs = {
            'users': args.users,
            'objects': args.objects,
            'max_sim_time': args.timesteps,
            'trace': None,
        }

        # Create simulation
        simulation = ConsistencySimulation.load(args.data[0], **kwargs)
        simulation.script()

        # Fetch workload from the simulation
        workload   = simulation.workload

        # If we're in manual mode, execute that and return.
        if args.debugging:
            return self.debugging_trace(workload, args)

        # Write the traces to disk
        for idx, access in enumerate(self.compute_accesses(workload, args.timesteps)):
            args.output.write("\t".join(access) + "\n")

        return (
            "traced {} accesses on {} objects by {} users over {} timesteps\n"
            "wrote the trace file to {}"
        ).format(
            idx+1, args.objects, args.users, args.timesteps, args.output.name
        )

    def compute_accesses(self, workload, until=None):
        # Determine the maximum simulation time
        until = until or settings.simulation.max_sim_time

        # Set up the access computation
        if isinstance(workload, Workload):
            workload = [workload]

        timestep = 0
        schedule = defaultdict(list)

        # Initialize the schedule
        for work in workload:
            schedule[int(work.next_access.get())].append(work)

        # Iterate through time
        while timestep < until:
            # Update the timestep to the next time in schedule
            timestep = min(schedule.keys())

            # Perform accesses for all scheduled workloads
            for work in schedule.pop(timestep):
                work.update()
                access = READ if work.do_read.get() else WRITE
                yield (str(timestep), work.device.id, work.current, access)

                # Reschedule the work
                schedule[int(work.next_access.get()) + timestep].append(work)

    def debugging_trace(self, workload, args):
        """
        Manual function to generate a debugging trace for specific workloads.
        """
        import random

        from operator import itemgetter
        from cloudscope.dynamo import CharacterSequence

        sequence = CharacterSequence(upper=True)

        nodes = defaultdict(dict)
        for idx, work in enumerate(workload):
            work.move()
            nodes[work]['dev'] = work.device.id
            nodes[work]['obj'] = [sequence.next() for _ in xrange(3)]
            nodes[work]['tme'] = 0
            nodes[work]['acs'] = WRITE

        output = []

        # Each node is going to access a single object
        for idx in xrange(1000):
            for work, info in nodes.items():
                info['tme'] += int(work.next_access.get())
                info['acs'] = READ if work.do_read.get() else WRITE

                output.append(
                    (info['tme'], info['dev'], random.choice(info['obj']), info['acs'])
                )

        for line in sorted(output, key=itemgetter(0)):
            args.output.write("\t".join((str(s) for s in line)) + "\n")

        return "manual debugging trace generated with {} accesses for {} devices".format(len(output), len(nodes))
