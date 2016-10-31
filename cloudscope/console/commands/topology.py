# cloudscope.console.commands.topology
# Generates homogenous topologies on demand
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Aug 26 14:04:27 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: topology.py [] benjamin@bengfort.com $

"""
Generates homogenous topologies on demand
"""

##########################################################################
## Imports
##########################################################################

import os
import json

from commis import Command
from itertools import cycle
from operator import itemgetter
from collections import Counter
from cloudscope.config import settings
from commis.exceptions import ConsoleError
from cloudscope.replica import ReplicaTypes
from cloudscope.experiment import compute_tick
from cloudscope.utils.decorators import memoized, setter


##########################################################################
## Constants
##########################################################################

SITE_NAMES = (
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "julia", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey",
    "xray", "yankee", "zulu",
)

##########################################################################
## Command
##########################################################################

class TopologyGeneratorCommand(Command):

    name = 'topology'
    help = 'generate homogenous, fully connected systems of varying sizes'
    args = {
        ('-n', '--nodes'): {
            "type": int,
            "metavar": "N",
            "required": True,
            "help": "number of nodes in the system",
        },
        ('-o', '--output'): {
            "default": None,
            "metavar": "PATH",
            "type": str,
            "help": "the location to write the simulation topology and traces out",
        },
        ('-l', '--locations'): {
            "type": int,
            "metavar": "N",
            "default": 5,
            "help": "number of locations in the system",
        },
        ('-t', '--type'): {
            "type": str,
            "metavar": "TYPE",
            "default": settings.simulation.default_replica,
            "help": "specify the replica type",
        },
        '--Lm': {
            "type": int,
            "default": 100,
            "dest": "local_mean",
            "help": 'local area connection mean latency',
        },
        '--Ls': {
            "type": int,
            "default": 5,
            "dest": "local_stddev",
            "help": 'local area connection latency standard deviation',
        },
        '--Wm': {
            "type": int,
            "default": 1000,
            "dest": "wide_mean",
            "help": 'wide area connection mean latency',
        },
        '--Ws': {
            "type": int,
            "default": 56,
            "dest": "wide_stddev",
            "help": 'wide area connection latency standard deviation',
        },
        '--tick-model': {
            'type': str,
            'default': 'bailis',
            'choices': ['howard', 'bailis', 'conservative', 'optimistic'],
            'metavar': 'method',
            'help': 'specify tick computation method based on latency',
        },
        'consistency': {
            "type": str,
            "nargs": 1,
            "choices": [rt.value for rt in ReplicaTypes['default'].keys()],
            "help": "specify the replica types to generate systems for.",
        }
    }

    def handle(self, args):
        """
        Instantiates a topology generator and generates the topology.
        """
        generator = TopologyGenerator(args)
        generator.generate_toplogy()
        generator.generate_trace()
        generator.generate_meta()
        generator.write()

        return "Created a {} topology with {} nodes in {} locations at {}".format(
            generator.consistency, generator.nodes, generator.n_locs, generator.output
        )

##########################################################################
## Topology Generator Object
##########################################################################

class TopologyGenerator(object):

    def __init__(self, args):
        self.nodes   = args.nodes
        self.n_locs  = args.locations
        self.local   = (args.local_mean, args.local_stddev)
        self.wide    = (args.wide_mean, args.wide_stddev)
        self.rtype   = args.type
        self.tick_model  = args.tick_model
        self.consistency = args.consistency[0]
        self.output      = args.output

        self.topology  = {
            'nodes': [],
            'links': [],
            'meta': {},
        }

        self.locations = cycle(SITE_NAMES[:self.n_locs])
        self.indices   = Counter()

    @setter
    def output(self, path):
        if path is None:
            path = "{}-{}.json".format(self.consistency, self.nodes)

        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        path = os.path.abspath(path)

        return path

    @memoized
    def tick_param(self):
        return compute_tick(*self.wide, model=self.tick_model)

    @memoized
    def anti_entropy_delay(self):
        return self.tick_param / 4

    @memoized
    def heartbeat_interval(self):
        return self.tick_param / 2

    @memoized
    def election_timeout(self):
        return (self.tick_param, 2*self.tick_param)

    def create_node(self):
        """
        Constructs the next node and appends it to the toplogy
        """
        # Figure out the next index/location allocation
        location = self.locations.next()
        index = self.indices[location]
        self.indices[location] += 1

        node = {
            "id": "{}{}".format(location[0].lower(), index),
            "label": "{} {}".format(location.title(), index),
            "location": "{}-site".format(location),
            "type": settings.simulation.default_replica,
            "consistency": self.consistency,
        }

        if self.consistency in {"eventual", "stentor"}:
            node["anti_entropy_delay"] = self.anti_entropy_delay
            node["sync_prob"]  = settings.simulation.sync_prob
            node["local_prob"] = settings.simulation.local_prob
            node["num_neighbors"] = settings.simulation.num_neighbors

        if self.consistency in {"raft", "tag", "strong"}:
            node["heartbeat_interval"] = self.heartbeat_interval
            node["election_timeout"] = self.election_timeout

        self.topology['nodes'].append(node)

    def create_links(self):
        """
        Generates a completely connected topology with specified latencies.
        """
        for idx, source in enumerate(self.topology['nodes']):
            for jdx, target in enumerate(self.topology['nodes']):
                # No self links in this graph
                if source['id'] == target['id']: continue

                link = {
                    "source": idx,
                    "target": jdx,
                    "connection": "normal",
                }

                if source['location'] == target['location']:
                    link['area'] = 'local'
                    link['latency'] = self.local

                else:
                    link['area'] = 'wide'
                    link['latency'] = self.wide

                self.topology['links'].append(link)

    def generate_toplogy(self):
        # Step one: generate nodes
        for _ in xrange(self.nodes):
            self.create_node()

        # Step two: sort the nodes by location
        self.topology['nodes'].sort(key=itemgetter('id'))

        # Step three: generate the links
        self.create_links()

    def generate_trace(self):
        # Step four: generate the trace if it doesn't exist
        self.trace = os.path.join(
            os.path.dirname(self.output), "traces",
            "workload-{}nodes-{}locations.tsv".format(self.nodes, self.n_locs)
        )

        if os.path.exists(self.trace):
            return

        if not os.path.exists(os.path.dirname(self.trace)):
            os.makedirs(os.path.dirname(self.trace))

        with open(self.trace, 'w') as f:
            f.write(
                "Please generate a workload for the topology at {}\n".format(
                    self.output
                )
            )
            f.write(
                "Should be for {} nodes in {} locations\n".format(
                    self.nodes, self.n_locs
                )
            )

    def generate_meta(self):
        # Step five: generate the meta data
        self.topology['meta']['title'] = "Homogenous {} System".format(self.consistency.title())
        self.topology['meta']['description'] = "A homogenous group of {} {} nodes in {} locations".format(self.nodes, self.consistency, self.n_locs)
        self.topology['meta']['seed'] = None
        self.topology['meta']['users'] = self.nodes
        self.topology['meta']['type'] = self.consistency
        self.topology['meta']['trace'] = self.trace
        self.topology['meta']['tick_metric'] = self.tick_param
        self.topology['meta']['tick_param_model'] = self.tick_model
        self.topology['meta']['local_latency'] = self.local
        self.topology['meta']['wide_latency'] = self.wide
        self.topology['meta']['latency_mean'] = self.wide[0]
        self.topology['meta']['latency_stddev'] = self.wide[1]
        self.topology['meta']['latency_range'] = (min(self.local[0], self.wide[0]), max(self.local[0], self.wide[0]))
        self.topology['meta']['constant'] = "N/A"
        self.topology['meta']['variable'] = "{}-{}ms".format(self.wide[0] - 2*self.wide[1], self.wide[0] + 2*self.wide[1])

        if self.consistency in {"eventual", "stentor"}:
            self.topology['meta']["anti_entropy_delay"] = self.anti_entropy_delay
            self.topology['meta']["sync_prob"]  = settings.simulation.sync_prob
            self.topology['meta']["local_prob"] = settings.simulation.local_prob
            self.topology['meta']["num_neighbors"] = settings.simulation.num_neighbors

        if self.consistency in {"raft", "tag", "strong"}:
            self.topology['meta']["heartbeat_interval"] = self.heartbeat_interval
            self.topology['meta']["election_timeout"] = self.election_timeout

    def write(self):
        with open(self.output, 'w') as f:
            json.dump(self.topology, f, indent=2)
