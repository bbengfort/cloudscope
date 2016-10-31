# -*- coding: utf-8 -*-
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
from cloudscope.simulation.outages import OutagesWriter
from cloudscope.simulation.main import ConsistencySimulation


##########################################################################
## Command
##########################################################################

class OutagesCommand(Command):

    name = 'outages'
    help = 'generate random outages script to write to disk'
    args = {
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
        Uses the OutagesWriter to generate an outages script. 
        """
        # Disable logging during trace generation
        logger = logging.getLogger('cloudscope.simulation')
        logger.disabled = True

        # Simulation arguments
        kwargs = {
            'max_sim_time': args.timesteps,
            'outages': None,
        }

        # Create simulation
        simulation = ConsistencySimulation.load(args.data[0], **kwargs)
        simulation.script()

        # Create the traces writer and write the traces to disk
        writer = OutagesWriter(simulation.partitions, args.timesteps)
        rows   = writer.write(args.output)

        return (
            "scripted {} outages on {} connections by {} generators "
            "over {} timesteps\n"
            "Outage probability was {} partitioned by '{}' strategy\n"
            "Online Distribution (ms) = {}μ {}σ\n"
            "Outage Distribution (ms) = {}μ {}σ\n"
            "wrote the script file to {}"
        ).format(
            rows, sum(len(gen.connections) for gen in simulation.partitions),
            len(simulation.partitions), args.timesteps,
            settings.simulation.outage_prob, settings.simulation.partition_across,
            settings.simulation.online_mean, settings.simulation.online_stddev,
            settings.simulation.outage_mean, settings.simulation.outage_stddev,
            args.output.name
        )
