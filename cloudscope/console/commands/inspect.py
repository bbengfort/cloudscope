# console.commands.inspect
# Prints out a table of the generated settings for experiments in a directory.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jul 12 15:19:08 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: inspect.py [] benjamin@bengfort.com $

"""
Prints out a table of the generated settings for experiments in a directory.
"""

##########################################################################
## Imports
##########################################################################

import os
import json

from commis import Command
from tabulate import tabulate
from collections import defaultdict
from cloudscope.console.commands.generate import csv


##########################################################################
## Module Constants
##########################################################################

EXCLUDE_SETTINGS = [
    'title', 'description', 'constant', 'variable', 'seed',
]


##########################################################################
## Command
##########################################################################

class InspectCommand(Command):

    name = "inspect"
    help = "print a table of settings for a list of experimental topologies"
    args = {
        ('-e', '--exclude'): {
            'type': csv(str),
            'metavar': 'KEY,KEY,...',
            'default': EXCLUDE_SETTINGS,
            'help': 'specify a list of settings to exclude for easier printing',
        },
        'topology': {
            'nargs': "+",
            'type': str,
            'default': None,
            'metavar': 'topology.json',
            'help': 'simulation topology file to load'
        }
    }

    def handle(self, args):
        """
        Returns a string representation of a table of all the settings.
        """
        # Create a data structure of observed settings
        settings = defaultdict(list)

        # Run through all the experimental topologies
        for path in self.all_topology_paths(args.topology):
            for key, val in self.read_meta_data(path).iteritems():
                if args.exclude and key in args.exclude: continue
                settings[key].append(val)

        # Return the tabulation
        return tabulate(settings, headers="keys")


    def list_json_files(self, path):
        """
        Returns the path of every file ending in .json in the given path.
        """
        for name in os.listdir(path):
            if name.endswith('.json'):
                yield os.path.join(path, name)

    def read_meta_data(self, path):
        """
        Reads and updates the meta data of the topology at the given path.
        """
        with open(path, 'r') as f:
            topo = json.load(f)

        # Extract the meta data from the topology
        meta = topo.get('meta', {})

        # Add the name of the experimental file
        meta['file']  = os.path.basename(path)

        # Count the number of nodes and links
        meta['nodes'] = len(topo['nodes'])
        meta['links'] = len(topo['links'])

        return meta

    def all_topology_paths(self, topologies):
        """
        Reads all topology paths and expands directories a single level.
        """
        for path in topologies:
            if os.path.isdir(path):
                for path in self.list_json_files(path):
                    yield path
            else:
                yield path
