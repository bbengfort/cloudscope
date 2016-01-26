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
                csim.replicas.append(Replica(**node))

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
        print self.replicas
        print self.network
