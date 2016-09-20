# cloudscope.console.commands.generate
# Command-line utility to generate a set of experiments from a file.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Feb 22 16:09:26 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: generate.py [26c65a7] benjamin@bengfort.com $

"""
Command-line utility to generate a set of experiments from a file.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import argparse

from copy import deepcopy
from commis import Command
from commis.exceptions import ConsoleError
from cloudscope.experiment import LatencyVariation
from cloudscope.experiment import AntiEntropyVariation
from cloudscope.experiment import FederatedLatencyVariation
from cloudscope.utils.serialize import JSONEncoder

##########################################################################
## Helpers
##########################################################################

def csv(type=int):
    """
    Argparse type for comma seperated values. Also parses the type, e.g. int.
    """
    def parser(s):
        try:
            parse = lambda p: type(p.strip())
            return map(parse, s.split(","))
        except Exception as e:
            raise argparse.ArgumentTypeError(
                "Could not parse CSV value to type {}: {!r}".format(type.__name__, s)
            )

    return parser

## Experiment Generators
generators = {
    'latency': LatencyVariation,
    'entropy': AntiEntropyVariation,
    'federated': FederatedLatencyVariation,
}

##########################################################################
## Command
##########################################################################

class GenerateCommand(Command):

    name = 'generate'
    help = 'generate a set of experiments from a topology template'
    args = {
        ('-o', '--output'): {
            'type': str,
            'metavar': 'DST',
            'required': True,
            'help': 'specify directory to write output to',
        },
        '--jitter': {
            'action': 'store_true',
            'default': False,
            'help': 'generate lots of experiments by randomizing outcomes',
        },
        ('-f', '--force'): {
            'action': 'store_true',
            'default': False,
            'help': 'overwrite the contents of a directory'
        },
        ('-n', '--count'): {
            'type': int,
            'metavar': 'NUM',
            'default': 12,
            'help': 'total number of permutations to generate',
        },
        ('-g', '--generator'): {
            'type': str,
            'choices': generators.keys(),
            'default': 'latency',
            'help': 'the experiment generator to use'
        },
        '--users': {
            'type': csv(int),
            'default': (1,5,2),
            'metavar': 'min,max,step',
            'help': 'specify the range of users in experiments',
        },
        '--traces': {
            'type': csv(str),
            'default': [],
            'metavar': 'trace, trace, ...',
            'help': 'specify a trace file or a trace per user range',
        },
        '--latency': {
            'type': csv(int),
            'default': (30,3000,None),
            'metavar': 'min,max,width',
            'help': 'specify the latency range in experiments',
        },
        '--anti-entropy': {
            'type': csv(int),
            'default': (100,1000),
            'metavar': 'min,max',
            'help': 'specify the anti-entropy delay range in experiments',
        },
        '--tick-metric': {
            'type': str,
            'default': 'conservative',
            'choices': ['howard', 'bailis', 'conservative', 'optimistic'],
            'metavar': 'method',
            'help': 'specify tick computation method based on latency',
        },
        'topology': {
            'nargs': 1,
            'type': argparse.FileType('r'),
            'default': None,
            'metavar': 'topology.json',
            'help': 'simulation description file to load',
        }
    }

    def handle(self, args):
        """
        Entry point for the simulation runner.
        """

        # Check the output directory
        outdir    = self.get_output_directory(args.output, args.force)

        # Get the name and extension of the topology
        topology  = args.topology[0]
        name, ext = os.path.splitext(os.path.basename(topology.name))

        idx =0
        # Generate the experiments and write them to disk
        for idx, experiment in enumerate(self.get_experiments(topology, args)):
            newname = "{}-{:0>2}{}".format(name, idx+1, ext)
            with open(os.path.join(outdir, newname), 'w') as o:
                json.dump(experiment, o, indent=2, cls=JSONEncoder)

        # Return a specification of what happened.
        return "Wrote {} experiments to {}".format(idx+1, outdir)

    def get_experiments(self, topology, args):
        """
        Handle to perform the experiment generation on the comamnd line.
        """
        # Get experimental arguments
        Generator = generators[args.generator]
        latency   = dict(zip(('minimum', 'maximum', 'max_range'), args.latency))
        users     = dict(zip(('minimum', 'maximum', 'step'), args.users))
        aentropy  = dict(zip(('minimum', 'maximum'), args.anti_entropy))
        traces    = args.traces
        tick      = {'method': args.tick_metric}
        generate  = Generator.load(
            topology, count=args.count, latency=latency, traces=traces,
            users=users, anti_entropy=aentropy, tick_metric=tick,
        )

        # Create an iterable of generators if jittering is required.
        generate = [generate] if not args.jitter else self.jitter(args.count, generate)

        # Yield experiments from all generators.
        for generator in generate:
            for experiment in generator:
                yield experiment

    def jitter(self, n, generate):
        """
        Randomizes the latency and the anti-entropy delay.
        """
        opts = deepcopy(generate.options)
        latency = opts['latency']
        aedelay = opts['anti_entropy']

        # Create +/- jitter in latency and aedelay
        for opt in (latency, aedelay):
            for k, v in opt.iteritems():
                opt[k] = (max(1, v-100), v+100)

        return generate.jitter(n, latency=latency, anti_entropy=aedelay)

    def get_output_directory(self, path, force=False):
        """
        Gets the normpath of the directory and checks that it exists and is
        a directory. Prompts if the current working directory is supplied.

        TODO: Simply create a directory with the experiment name.
        """
        path = os.path.abspath(path)

        # Make the path if it does not exist
        if not os.path.exists(path):
            os.makedirs(path)

        if not os.path.isdir(path):
            raise ConsoleError(
                "{!r} is not a directory!".format(path)
            )

        if os.listdir(path):
            if not force:
                raise ConsoleError(
                    "{!r} is not empty!".format(path)
                )

        return path
