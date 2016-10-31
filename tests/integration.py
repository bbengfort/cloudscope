# tests.integration
# Integration testing - executes a complete simulation to look for errors.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Apr 04 09:02:14 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: integration.py [448d930] benjamin@bengfort.com $

"""
Integration testing - executes a complete simulation to look for errors.
Note that this style of testing is officially run in:

    tests/test_simulation/test_main.py

However, this package provides tools to easily allow import and play with the
integration tests for development purposes. (No tests will be run here).
"""

##########################################################################
## Imports
##########################################################################

import os

from cloudscope.simulation.main import ConsistencySimulation

##########################################################################
## Fixtures
##########################################################################

# Paths to load the test topologies
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
RAFT     = os.path.join(FIXTURES, "raft.json")
EVENTUAL = os.path.join(FIXTURES, "eventual.json")
TAG      = os.path.join(FIXTURES, "tag.json")

# Default Options for the simulations
OPTIONS  = {
    'max_sim_time': 100000,
    'objects': 10,
}

##########################################################################
## Simulation Loader
##########################################################################

def getsim(topology='tag', **kwargs):
    # Find the correct topology
    topology = {
        'tag': TAG,
        'raft': RAFT,
        'eventual': EVENTUAL,
    }[topology.lower()]

    # Update the default options
    options = OPTIONS.copy()
    options.update(kwargs)

    # Load the simulation
    with open(topology, 'r') as fobj:
        sim = ConsistencySimulation.load(fobj, **options)

    return sim

if __name__ == '__main__':

    import argparse

    # Parse the arguments from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'topology', choices=['tag', 'eventual', 'raft'], default='tag', nargs='?',
        help='Specify the simulation topology to load.'
    )

    args = parser.parse_args()
    sim = getsim(args.topology)
    sim.run()

    print sim.results.results.keys()
