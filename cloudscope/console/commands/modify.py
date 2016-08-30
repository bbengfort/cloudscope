# cloudscope.console.commands.modify
# Modifies topologies in place for deploying to alternative sites.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Aug 12 11:36:41 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: modify.py [] benjamin@bengfort.com $

"""
Modifies topologies in place for deploying to alternative sites.
The original version of this script resets local paths for the traces and
modifies local and wide area latency for nodes.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import argparse
import warnings

from commis import Command
from commis.exceptions import ConsoleError
from cloudscope.experiment import compute_tick


##########################################################################
## Key/Value Type
##########################################################################

def keyval(string):
    """
    Parses a key/value pair from the command line.
    """
    pairs = [
        map(lambda s: s.strip(), pair.split("="))
        for pair in string.split("&")
    ]

    if not all([len(pair) == 2 for pair in pairs]):
        raise argparse.ArgumentTypeError(
            "Must pass key/value pairs as key1=value1&key2=value2"
        )

    return dict(pairs)


##########################################################################
## Command
##########################################################################

class ModifyTopologyCommand(Command):

    name = 'modify'
    help = 'modifies a topology in place with new information'
    args = {
        '--Lm': {
            "type": int,
            "default": None,
            "dest": "local_mean",
            "help": 'modify the local area connection mean latencies',
        },
        '--Ls': {
            "type": int,
            "default": None,
            "dest": "local_stddev",
            "help": 'modify the local area connection latency standard deviation',
        },
        '--Wm': {
            "type": int,
            "default": None,
            "dest": "wide_mean",
            "help": 'modify the wide area connection mean latencies',
        },
        '--Ws': {
            "type": int,
            "default": None,
            "dest": "wide_stddev",
            "help": 'modify the wide area connection latency standard deviation',
        },
        ('-T', '--traces'): {
            "metavar": "PATH",
            "default": None,
            "help": "specify a directory or trace to replace traces information",
        },
        ('-M', '--meta'): {
            "metavar": "KEY=VAL",
            "default": None,
            "type": keyval,
            "help": "specify key/value pairs to modify in the meta data",
        },
        'topologies': {
            'nargs': '+',
            'metavar': 'topo.json',
            'help': 'path(s) to the experiment topologies to modify',
        }
    }

    def handle(self, args):
        """
        Handles the modification of one or more topology files, collecting
        information about how many edits are being made in the topology.
        """
        mods = 0 # Track how many key/value pairs are being modified.
        for path in args.topologies:
            mods += self.modify_topology(path, args)

        return "Modified {} key/value pairs in {} topologies".format(
            mods, len(args.topologies)
        )

    def modify_topology(self, path, args):
        """
        Modifies a topology in a file-like object with data input from the
        command line, tracking how many changes are made at each point.
        """
        # Load the topology data
        with open(path, 'r') as fobj:
            topo = json.load(fobj)

        # Track the number of modifications
        mods = 0

        # If the local area parameters have been passed in, modify them.
        if args.local_mean or args.local_stddev:
            mods += self.modify_local_network(
                topo, args.local_mean, args.local_stddev
            )

        # If the wide area parameters have been passed in, modify them.
        if args.wide_mean or args.wide_stddev:
            mods += self.modify_wide_network(
                topo, args.wide_mean, args.wide_stddev
            )

        # If new traces have been passed in, modify it.
        if args.traces:
            mods += self.modify_traces(
                topo, args.traces
            )

        # Modify the meta data with the new information.
        mods += self.modify_meta_info(topo, args)

        # Dump the topology that has been modified back to disk.
        # TODO: should we check if we've made any modifications before this?
        with open(path, 'w') as fobj:
            json.dump(topo, fobj, indent=2)

        return mods

    def modify_local_network(self, topo, mean, stddev):
        """
        Modifies local area connections according to the network mean and
        standard deviation. Returns number of modifications.
        """
        # Modifications
        mods = 0

        # Must supply both the mean and the stddev
        if not mean or not stddev:
            raise ConsoleError(
                "Must supply both the local mean and local standard deviation!"
            )

        # Modify the local links only!
        for link in topo['links']:
            if link['area'] == 'local':
                mods += self.update_dict_value(link, 'latency', (mean, stddev))

        # Modify the meta data about local connections
        mods += self.update_meta_param(topo, 'local_latency', (mean, stddev))
        return mods

    def modify_wide_network(self, topo, mean, stddev):
        """
        Modifies wide area connections according to the network mean and
        standard deviation. This function will also update timing parameters
        of the nodes according to the tick; it will also necessarily update
        some of the meta information. Returns number of modifications.
        """

        # Modifications
        mods = 0

        # Must supply both the mean and the stddev
        if not mean or not stddev:
            raise ConsoleError(
                "Must supply both the wide mean and wide standard deviation!"
            )

        # Compute the tick parameter and timing params
        tick_model = model=topo['meta'].get('tick_param_model', 'bailis')
        T = compute_tick(mean, stddev, tick_model)

        # Timing parameters for individual nodes
        eto = (T, 2*T)
        hbi = T/2
        aed = T/4

        # Modify each node's timing parameters
        for node in topo['nodes']:

            if 'election_timeout' in node:
                mods += self.update_dict_value(node, 'election_timeout', eto)

            if 'heartbeat_interval' in node:
                mods += self.update_dict_value(node, 'heartbeat_interval', hbi)

            if 'anti_entropy_delay' in node:
                mods += self.update_dict_value(node, 'anti_entropy_delay', aed)

        # Modify the wide links only!
        for link in topo['links']:
            if link['area'] == 'wide':
                mods += self.update_dict_value(link, 'latency', (mean, stddev))

        # Modify the meta data
        mods += self.update_meta_param(topo, 'tick_param_model', tick_model)
        mods += self.update_meta_param(topo, 'wide_latency', (mean, stddev))
        mods += self.update_meta_param(topo, 'anti_entropy_delay', aed)
        mods += self.update_meta_param(topo, 'election_timeout', eto)
        mods += self.update_meta_param(topo, 'heartbeat_interval', hbi)
        mods += self.update_meta_param(topo, 'latency_mean', mean)
        mods += self.update_meta_param(topo, 'latency_stddev', stddev)
        mods += self.update_meta_param(topo, 'tick_metric', T)
        mods += self.update_meta_param(topo, 'variable', "{}-{}ms".format(
            mean - 2*stddev, mean + 2*stddev)
        )

        return mods

    def modify_traces(self, topo, traces):
        """
        Modifies the traces inside the meta data of the topology. Returns the
        number of modifications made.
        """
        # Modifications
        mods = 0

        if os.path.isdir(traces):
            # Replace the metadata trace with a new directory
            name = os.path.basename(topo['meta']['trace'])
            path = os.path.abspath(os.path.join(traces, name))

            # Quick check to make sure the trace exists
            if not os.path.exists(path):
                raise ConsoleError(
                    "Trace at {} does not exist!".format(path)
                )

            mods += self.update_meta_param(topo, 'trace', path)

        elif os.path.isfile(traces):
            # Replace the trace with the specified file.
            mods += self.update_meta_param(topo, 'trace', traces)

        else:
            raise ConsoleError(
                "Supply either a valid directory or path to a trace!"
            )

        return mods

    def modify_meta_info(self, topo, args):
        """
        Finalizes the meta information of the topology according to any global
        changes that may have been made and need to be tracked. Returns the
        total number of modifications made to the topology meta info.
        """
        # Modifications
        mods = 0

        # Modify the overall latency range
        local = topo['meta'].get('local_latency', [None, None])[0]
        wide  = topo['meta'].get('wide_latency', [None, None])[0]
        lrng  = [min(local, wide), max(local, wide)]
        mods += self.update_meta_param(topo, 'latency_range', lrng)

        if args.meta:
            for key, val in args.meta.items():
                mods += self.update_meta_param(topo, key, val)

        return mods

    def update_dict_value(self, item, key, value):
        """
        Updates a value in the dictionary if the supplied value doesn't match
        the value for that key and returns 1, otherwise returns 0.
        """
        if item.get(key, None) != value:
            item[key] = value
            return 1
        return 0

    def update_meta_param(self, topo, key, value):
        """
        Updates a meta data parameter if the supplied key doesn't match the
        value and returns 1 otherwise returns 0.
        """
        return self.update_dict_value(topo['meta'], key, value)
