# console.commands.inspect
# Prints out a table of the generated settings for experiments in a directory.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jul 12 15:19:08 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: inspect.py [b62bcba] benjamin@bengfort.com $

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

ENVIRONMENT_KEYS = [
    'type', 'users', 'nodes', 'links', 'wide_latency', 'local_latency',
]

EVENTUAL_KEYS = [
    'anti_entropy_delay', 'local_prob', 'sync_prob', 'num_neighbors',
]

RAFT_KEYS = [
    'election_timeout', 'heartbeat_interval',
]

TIMING_KEYS = [
    'latency_mean', 'latency_stddev', 'latency_range', 'tick_param_model', 'tick_metric',
]

WORKLOAD_KEYS = [
    'conflict_prob', 'trace', 'users',
]

TABLE_FORMATS = [
    "plain", "simple", "grid", "fancy_grid", "pipe", "orgtbl", "rst",
    "mediawiki", "html", "latex", "latex_booktabs",
]

##########################################################################
## Command
##########################################################################

class InspectCommand(Command):

    name = "inspect"
    help = "print a table of settings for a list of experimental topologies"
    args = {
        ('-k', '--aggregator'):{
            'type': str,
            'default': None,
            'help': 'specify a key to aggregate the table upon',
        },
        ('-t', '--tablefmt'): {
            'type': str,
            'choices': TABLE_FORMATS,
            'default': 'simple',
            'help': 'specify the output format of the table',
        },
        ('-e', '--exclude'): {
            'type': csv(str),
            'metavar': 'KEY,KEY,...',
            'default': EXCLUDE_SETTINGS,
            'help': 'specify a list of settings to exclude for easier printing',
        },
        ('-i', '--include'): {
            'type': csv(str),
            'metavar': 'KEY,KEY,...',
            'default': None,
            'help': 'specify only the settings to be displayed',
        },
        ('-s', '--show-keys'): {
            'action': 'store_true',
            'default': False,
            'help': 'list the keys in the topologies and exit',
        },
        ('-E', '--environment'): {
            'action': 'store_true',
            'default': False,
            'help': 'quick helper to show environment related keys',
        },
        ('-B', '--eventual'): {
            'action': 'store_true',
            'default': False,
            'help': 'quick helper to show eventual consistency related keys',
        },
        ('-R', '--raft'): {
            'action': 'store_true',
            'default': False,
            'help': 'quick helper to show raft related keys',
        },
        ('-W', '--workload'): {
            'action': 'store_true',
            'default': False,
            'help': 'quick helper to show workload related keys',
        },
        ('-T', '--timing'): {
            'action': 'store_true',
            'default': False,
            'help': 'quick helper to show timing related keys',
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
        # If we're only showing keys, don't exclude anything
        if args.show_keys: args.exclude = []

        # Quick helper for fixed key sets preloaded into the command
        flags = [args.environment, args.eventual, args.raft, args.timing, args.workload]
        fixed_keys = [ENVIRONMENT_KEYS, EVENTUAL_KEYS, RAFT_KEYS, TIMING_KEYS, WORKLOAD_KEYS]
        for flag, keys in zip(flags, fixed_keys):
            if flag:
                if args.include:
                    args.include += keys
                else:
                    args.include = keys

        # If key in both include and exclude, remove from exclude
        if args.include:
            for key in args.include:
                if key in args.exclude: args.exclude.remove(key)

        # If we have a key to aggregate on, aggregate by it.
        # Aggregation mechanism is currently just set for now.
        if args.aggregator:
            settings = self.inspect_by_aggregator(args)
        else:
            settings = self.inspect_topologies(args)

        # Show only the keys column
        if args.show_keys:
            keys = [[key] for key in sorted(settings.keys())]
            return tabulate(keys, headers=['available keys'], tablefmt=args.tablefmt)

        # Sort the table by keys
        headers = sorted(settings.keys())

        # Either file, settings, or type should be the first column.
        for fcoln in ('setting', 'file', 'type'):
            if fcoln in headers:
                headers.insert(0, headers.pop(headers.index(fcoln)))
                break

        # Right now the data format is a dictionary of lists; convert to
        # ensure that the sorted header order is maintained in the table.
        table = []
        for col, header in enumerate(headers):
            for row, value in enumerate(settings[header]):
                if col == 0: table.append([])
                table[row].append(value)

        # Return the tabulation
        return tabulate(table, headers=headers, tablefmt=args.tablefmt)

    def inspect_topologies(self, args):
        """
        Returns a simple table where the columns are each key in the settings
        of the topology files and each row is the values for an individual
        topology file.
        """
        # Create a data structure of observed settings
        settings = defaultdict(list)

        # Run through all the experimental topologies
        for path in self.all_topology_paths(args.topology):
            for key, val in self.read_meta_data(path).iteritems():
                if args.exclude and key in args.exclude: continue
                if args.include and key not in args.include: continue
                settings[key].append(val)

        return settings

    def inspect_by_aggregator(self, args):
        """
        Returns an inverted table of settings where each coloumn are the
        unique values of the aggregator key (usually type or title) and the
        rows are the key/value pairs for all topologies of that aggregator
        value (the setting is specified as it's own row).
        """
        aggkey   = args.aggregator
        settings = defaultdict(lambda: defaultdict(set))
        allkeys  = set()

        # Run through all the experimental topologies
        for path in self.all_topology_paths(args.topology):
            # Read data and check for aggregator key
            meta = self.read_meta_data(path)
            if aggkey not in meta:
                raise Exception(
                    "Could not find key '{}' in {}".format(aggkey, path)
                )

            # Go through all the key/value pairs, excluding keys as needed
            for key, val in meta.iteritems():
                if key == aggkey: continue
                if args.exclude and key in args.exclude: continue
                if args.include and key not in args.include: continue

                # if val is a list, make it a tuple
                if isinstance(val, list):
                    val = tuple(val)

                # aggregate on aggkey values
                settings[meta[aggkey]][key].add(val)

                # keep track of all unique keys
                allkeys.add(key)

        # Pivot the table for use in tabulate
        pivot = defaultdict(list)
        allkeys = sorted(allkeys)
        pivot['setting'] = allkeys

        # col is the aggregated values and rows are dictionaries of sets.
        for col, rows in settings.iteritems():
            for key in allkeys:
                val = rows.get(key, None)
                if val is None:
                    pivot[col].append(None)
                elif len(val) == 1:
                    pivot[col].append(val.pop())
                else:
                    pivot[col].append(", ".join([str(i) for i in val]))

        return pivot

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

    def list_json_files(self, path):
        """
        Returns the path of every file ending in .json in the given path.
        """
        for name in os.listdir(path):
            if name.endswith('.json'):
                yield os.path.join(path, name)
