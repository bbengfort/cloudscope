# generate
# Generates the scaling topology experiments.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Oct 20 16:32:56 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: generate.py [] benjamin@bengfort.com $

"""
Generates the scaling topology experiments.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import logging

from cStringIO import StringIO
from itertools import combinations
from cloudscope.config import settings
from cloudscope.experiment import compute_tick
from cloudscope.simulation.main import ConsistencySimulation
from cloudscope.simulation.workload.traces import TracesWriter


##########################################################################
## Module Constants
##########################################################################

BASEDIR     = os.path.abspath(os.path.dirname(__file__))
TRACES      = os.path.join(BASEDIR, "traces")
TRACENAME   = "workload-{}nodes-{}locations.tsv"
TOPONAME    = "{}-{}.json"

MAX_NODES   = 150
N_LOCATIONS = 5
LOCATIONS   = [
    'alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf', 'hotel',
    'india', 'juliet', 'kilo', 'lima', 'mike', 'november', 'oscar', 'papa',
    'quebec', 'romeo', 'sierra', 'tango', 'uniform', 'victor', 'whiskey',
    'xray', 'yankee', 'zulu',
]

WIDE_LATENCY_MU = 300
WIDE_LATENCY_SIGMA = 50
LOCAL_LATENCY_MU = 30
LOCAL_LATENCY_SIGMA = 5

TICK_MODEL = "bailis"
T = compute_tick(WIDE_LATENCY_MU, WIDE_LATENCY_SIGMA, TICK_MODEL)
SYSTEMS = ['eventual', 'raft']

NODE_KEYS = {
    "id": None,
    "label": None,
    "type": "storage",
    "location": None,
}

EVENTUAL_NODE_KEYS = {
    "consistency": "eventual",
    "anti_entropy_delay": int(round(float(T) / 4.0)),
    "num_neighbors": 1,
}

RAFT_NODE_KEYS = {
    "consistency": "raft",
    "election_timeout": [T, 2*T],
    "heartbeat_interval": int(round(float(T) / 2.0)),
}

LINK_KEYS = {
  "source": None,
  "target": None,
  "connection": "normal",
  "latency": None,
  "area": None,
}

META_KEYS = {
    "seed": None,
    "type": None,
    "title": "Homogenous {} System",
    "description": "A homogenous group of {} {} nodes in {} locations",
    "users": None,
    "trace": None,
    "constant": "N/A",
    "variable": "{}-{}ms".format((LOCAL_LATENCY_MU - 2*LOCAL_LATENCY_SIGMA), (WIDE_LATENCY_MU + 2*WIDE_LATENCY_SIGMA)),
    "tick_param_model": TICK_MODEL,
    "tick_metric": T,
    "latency_mean": WIDE_LATENCY_MU,
    "latency_stddev": WIDE_LATENCY_SIGMA,
    "latency_range": [(LOCAL_LATENCY_MU - 2*LOCAL_LATENCY_SIGMA), (WIDE_LATENCY_MU + 2*WIDE_LATENCY_SIGMA)],
    "wide_latency": [WIDE_LATENCY_MU, WIDE_LATENCY_SIGMA],
    "local_latency": [LOCAL_LATENCY_MU, LOCAL_LATENCY_SIGMA],
    "anti_entropy_delay": int(round(float(T) / 4.0)),
    "num_neighbors": 1,
    "election_timeout": [T, 2*T],
    "heartbeat_interval": int(round(float(T) / 2.0)),
}


N_OBJECTS = 15
CONFLICT  = 0.4
ACCESS_MU = 3500
ACCESS_SIGMA = 380
TIMESTEPS = 4640000


def get_nodes(num_nodes, node_type, num_locs=N_LOCATIONS):
    locations = LOCATIONS[:num_locs]
    nodes_per = num_nodes / num_locs

    for loc in locations:
        for idx in xrange(nodes_per):
            # Create the node dictionary
            node = NODE_KEYS.copy()

            # Update eventual properties
            if node_type == 'eventual':
                node.update(EVENTUAL_NODE_KEYS.copy())

            # Update Raft properties
            if node_type == 'raft':
                node.update(RAFT_NODE_KEYS.copy())

            # Update node description
            node['id'] = "{}{}".format(loc[0], idx)
            node['label'] = "{} {}".format(loc.title(), idx)
            node['location'] = "{}-site".format(loc)

            yield node


def create_topology(num_nodes, node_type, num_locs=N_LOCATIONS):
    topology = {
        'nodes': [], 'links': [], 'meta': META_KEYS.copy(),
    }

    # Add the meta information
    topology['meta']['type'] = node_type
    topology['meta']['title'] = topology['meta']['title'].format(node_type.title())
    topology['meta']['description'] = topology['meta']['description'].format(num_nodes, node_type, num_locs)
    topology['meta']['users'] = num_nodes
    topology['meta']['trace'] = os.path.join(TRACES, TRACENAME.format(num_nodes, num_locs))

    # Create the nodes
    topology['nodes'] = list(get_nodes(num_nodes, node_type, num_locs))

    # Create the links
    for (idx, nodea), (jdx, nodeb) in combinations(enumerate(topology['nodes']), 2):
        link = LINK_KEYS.copy()

        link['source'] = idx
        link['target'] = jdx

        if nodea['location'] != nodeb['location']:
            link['area'] = 'wide'
            link['latency'] = [WIDE_LATENCY_MU, WIDE_LATENCY_SIGMA]
        else:
            link['area'] = 'local'
            link['latency'] = [LOCAL_LATENCY_MU, LOCAL_LATENCY_SIGMA]

        topology['links'].append(link)

    name = TOPONAME.format(node_type, num_nodes)
    with open(name, 'w') as f:
        json.dump(topology, f, indent=2)

    return topology


def create_trace(topof, num_nodes, num_locs=N_LOCATIONS, num_objs=N_OBJECTS,
                 conflict=CONFLICT, Am=ACCESS_MU, As=ACCESS_SIGMA,
                 ts=TIMESTEPS):

    # Modify parameters
    # Disable logging during trace generation
    logger = logging.getLogger('cloudscope.simulation')
    logger.disabled = True

    # Update settings arguments
    settings.simulation.conflict_prob = conflict
    settings.simulation.access_mean   = Am
    settings.simulation.access_stddev = As

    # Simulation arguments
    kwargs = {
        'users': num_nodes,
        'objects': num_objs,
        'max_sim_time': ts,
        'trace': None,
    }

    # Create simulation
    simulation = ConsistencySimulation.load(topof, **kwargs)
    simulation.trace = None
    simulation.script()
    workload = simulation.workload

    # Create the traces writer and write the traces to disk
    writer = TracesWriter(workload, ts)
    outpath = os.path.join(TRACES, TRACENAME.format(num_nodes, num_locs))

    with open(outpath, 'w') as f:
        counts = writer.write(f)


def create_topof(topo):
    topof = StringIO()
    json.dump(topo, topof)
    topof.seek(0)
    return topof

if __name__ == '__main__':

    for num_nodes in xrange(N_LOCATIONS, MAX_NODES, N_LOCATIONS):
        topo = create_topology(num_nodes, 'eventual')
        topo = create_topology(num_nodes, 'raft')

        topof = create_topof(topo)
        create_trace(topof, num_nodes)
