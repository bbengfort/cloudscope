# cloudscope.simulation.main
# The primary consistency fragmentation simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 05:28:30 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: main.py [945ecd7] benjamin@bengfort.com $

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
from cloudscope.simulation.workload import create as create_workload
from cloudscope.utils.serialize import JSONEncoder
from cloudscope.replica import replica_factory

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

            # Add simulation meta information
            csim.name = data['meta']['title']
            csim.description = data['meta']['description']
            csim.users = data['meta'].get('users', csim.users)

            # Add replicas to the simulation
            for node in data['nodes']:
                csim.replicas.append(replica_factory(csim, **node))

            # Add edges to the network graph
            for link in data['links']:
                source = csim.replicas[link.pop('source')]
                target = csim.replicas[link.pop('target')]
                csim.network.add_connection(source, target, True, **link)

        return csim

    def __init__(self, **kwargs):
        super(ConsistencySimulation, self).__init__(**kwargs)

        # Primary simulation variables.
        self.users    = kwargs.get('users', settings.simulation.users)
        self.replicas = []
        self.network  = Network()

    def complete(self):
        """
        Ensure the topology is part of the results, as well as any configured
        variables on that don't match the settings.
        """
        self.results.settings['users'] = self.users
        self.results.topology = self.serialize()

        # Compute Anti-Entropy
        aedelays = map(float, [
            node.ae_delay for node in
            filter(lambda n: n.consistency =="low", self.replicas)
        ])

        if aedelays:
            self.results.settings['anti_entropy_delay'] = int(sum(aedelays) / len(aedelays))

        super(ConsistencySimulation, self).complete()

    def script(self):
        self.workload = [
            create_workload(self.env, self)
            for user in xrange(self.users)
        ]

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
                'description': getattr(self, 'description', None),

                # Latency Labels
                'constant': '{}ms'.format(latency.get('constant', ('N/A ', None))[0]),
                'variable': '{}-{}ms'.format(*latency.get('variable', ('N/A','N/A'))),
            },
        }
