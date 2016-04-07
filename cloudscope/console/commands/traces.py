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
        ('-o', '--output'): {
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
        # Create simulation
        simulation = ConsistencySimulation.load(args.data[0])
        simulation.script()

        # Fetch workload from the simulation
        workload   = simulation.workload

        # Write the traces to disk
        for idx, access in enumerate(self.compute_accesses(workload)):
            args.output.write("\t".join(access) + "\n")

        return "wrote {} accesses to {}".format(idx+1, args.output.name)

    def compute_accesses(self, workload):
        # Set up the access computation
        if isinstance(workload, Workload):
            workload = [workload]

        timestep = 0
        schedule = defaultdict(list)

        # Initialize the schedule
        for work in workload:
            schedule[int(work.next_access.get())].append(work)

        # Iterate through time
        while timestep < settings.simulation.max_sim_time:
            # Update the timestep to the next time in schedule
            timestep = min(schedule.keys())

            # Perform accesses for all scheduled workloads
            for work in schedule.pop(timestep):
                work.update()
                access = READ if work.do_read.get() else WRITE
                yield (str(timestep), work.device.id, work.current, access)

                # Reschedule the work
                schedule[int(work.next_access.get()) + timestep].append(work)
