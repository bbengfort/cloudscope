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
import argparse

from operator import itemgetter
from collections import defaultdict

from commis import Command
from cloudscope.config import settings
from cloudscope.dynamo import CharacterSequence
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
        if args.best_case:
            return self.best_case_trace(workload, args)

        if args.ping_pong:
            return self.ping_pong_trace(workload, args)

        if args.tiered:
            return self.tiered_trace(workload, args)

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

    def best_case_trace(self, workload, args):
        """
        Manual function to generate a "best case" trace for tagging: that is
        where each replica server only accesses its own objects.
        """
        until    = args.timesteps
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
                if info['tme'] > until:
                    break

                info['acs'] = READ if work.do_read.get() else WRITE

                output.append(
                    (info['tme'], info['dev'], random.choice(info['obj']), info['acs'])
                )

        for line in sorted(output, key=itemgetter(0)):
            args.output.write("\t".join((str(s) for s in line)) + "\n")

        return "manual \"best case\" trace generated with {} accesses for {} devices".format(len(output), len(nodes))

    def ping_pong_trace(self, workload, args):
        """
        Manual trace generation function to create a "ping pong" scenario
        where the tag bounces between replica servers.
        """
        until = args.timesteps
        tag   = ['A', 'B', 'C', 'D', 'E']
        time  = 0
        nodes = {work.device.id: work for work in workload if not work.move()}
        bingo = random.choice(nodes.keys())
        work  = nodes[bingo]
        N     = 5000

        for idx in xrange(N):

            # Do we switch to a new writer with some small probability?
            if random.random() < 0.1:
                bingo = random.choice(nodes.keys())

            # Update the time and determine the access
            time  += int(work.next_access.get())
            if time > until:
                break

            # Write the random
            obj    = random.choice(tag)
            access = READ if work.do_read.get() else WRITE

            # Write out the trace
            args.output.write(
                "{}\t{}\t{}\t{}\n".format(time, bingo, obj, access)
            )

        return "manual \"ping pong\" trace generated with {} accesses for {} devices".format(idx+1, len(nodes))

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
