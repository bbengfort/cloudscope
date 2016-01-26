# cloudscope.simulation.main
# The primary consistency fragmentation simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 05:28:30 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: main.py [] benjamin@bengfort.com $

"""
The primary consistency fragmentation simulation.
"""

##########################################################################
## Imports
##########################################################################

import json
import simpy

from cloudscope.config import settings
from cloudscope.simulation import Simulation
from cloudscope.simulation.network import Network
from cloudscope.simulation.replica import Replica
from cloudscope.utils.serialize import JSONEncoder

##########################################################################
## Primary Simulation
##########################################################################

class ConsistencySimulation(Simulation):

    @classmethod
    def load(klass, fobj, **kwargs):
        """
        Loads the simulation network from a JSON file containing the
        simulation description and network graph.
        """
        csim = klass(**kwargs)

        if fobj is not None:
            data = json.load(fobj)

            # Add replicas to the simulation
            for node in data['nodes']:
                csim.replicas.append(Replica(csim, **node))

            # Add edges to the network graph
            for link in data['links']:
                source = csim.replicas[link.pop('source')]
                target = csim.replicas[link.pop('target')]
                csim.network.add_connection(source, target, True, **link)

        return csim

    def __init__(self, **kwargs):
        super(ConsistencySimulation, self).__init__(**kwargs)

        # Primary simulation variables.
        self.replicas = []
        self.network  = Network()

    def script(self):
        import random

        def messenger(env):
            for idx in xrange(20):
                yield env.timeout(random.randint(20, 1000))
                conn = random.choice(list(self.network))
                conn.source.send(conn.target, "hello world {}!".format(idx))

        self.env.process(messenger(self.env))

    def dump(self, fobj, **kwargs):
        """
        Write the simulation to disk as a D3 JSON Graph
        """
        return json.dump(self, fobj, cls=JSONEncoder, **kwargs)

    def serialize(self):
        latency = self.network.get_latency_ranges()
        network = self.network.serialize()

        return {
            'nodes': network['nodes'],
            'links': network['links'],
            'meta':  {
                'seed': self.random_seed,
                'title': self.name,

                # Latency Labels
                'constant': '{}ms'.format(latency['constant'][0]),
                'variable': '{}-{}ms'.format(*latency['variable']),
            },
        }
