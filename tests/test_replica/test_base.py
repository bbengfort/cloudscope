# tests.test_replica.test_base
# Testing for the base mechanics and methods of replicas.
#
# Author:   Benjamin Bengfort <bbengfort@districtdatalabs.com>
# Created:  Fri Aug 19 07:21:58 2016 -0400
#
# Copyright (C) 2016 District Data Labs
# For license information, see LICENSE.txt
#
# ID: test_base.py [] benjamin@bengfort.com $

"""
Testing for the base mechanics and methods of replicas.
"""

##########################################################################
## Imports
##########################################################################

import unittest


try:
    from unittest import mock
except ImportError:
    import mock

from cloudscope.config import settings
from cloudscope.replica.base import Replica
from cloudscope.simulation.main import ConsistencySimulation
from cloudscope.replica.base import State, Consistency, Location

##########################################################################
## Base Replica Test Cases
##########################################################################


class BaseReplicaTests(unittest.TestCase):

    def setUp(self):
        self.sim = ConsistencySimulation()
        Replica.counter.reset()

    def tearDown(self):
        self.sim = None

    def test_replica_defaults(self):
        """
        Test that a base replica has meaningful defaults
        """
        replica = Replica(self.sim)

        self.assertIsNotNone(replica.id)
        self.assertEqual(replica.type, settings.simulation.default_replica)
        self.assertIsNotNone(replica.label)
        self.assertEqual(replica.state, State.READY)
        self.assertEqual(replica.location, "unknown")
        self.assertEqual(
            replica.consistency, Consistency.get(settings.simulation.default_consistency)
        )

    def test_increasing_replica_ids(self):
        """
        Test that replicas get an increasing id by default
        """
        for idx in xrange(10):
            replica = Replica(self.sim)
            self.assertEqual(replica.id, "r{}".format(idx+1))

    def test_on_state_change_calls(self):
        """
        Ensure that on state change event handler is called
        """
        replica = Replica(self.sim)
        replica.on_state_change = mock.MagicMock()

        states = (
            State.UNKNOWN, State.LOADING, State.ERRORED,
            State.READY, State.FOLLOWER, State.CANDIDATE, State.TAGGING,
            State.LEADER, State.OWNER
        )

        for state in states:
            replica.state = state
            replica.on_state_change.assert_called_with()

        self.assertEqual(replica.on_state_change.call_count, len(states))

    def build_neighbors(self):
        """
        Helper function to add a bunch of replicas to the simulation for
        neighborhood testing that follows below.
        """

        # Add a bunch of replicas to the simulation
        replicas = [
            {"consistency":Consistency.STRONG, "location":Location.ALPHA},
            {"consistency":Consistency.EVENTUAL, "location":Location.ALPHA},
            {"consistency":Consistency.EVENTUAL, "location":Location.ALPHA},
            {"consistency":Consistency.STRONG, "location":Location.BRAVO},
            {"consistency":Consistency.EVENTUAL, "location":Location.BRAVO},
            {"consistency":Consistency.CAUSAL, "location":Location.BRAVO},
            {"consistency":Consistency.STRONG, "location":Location.BRAVO},
            {"consistency":Consistency.EVENTUAL, "location":Location.BRAVO},
            {"consistency":Consistency.CAUSAL, "location":Location.BRAVO},
            {"consistency":Consistency.CAUSAL, "location":Location.CHARLIE},
            {"consistency":Consistency.CAUSAL, "location":Location.CHARLIE},
        ]

        # Add replicas to the simulation
        for kwargs in replicas:
            self.sim.replicas.append(Replica(self.sim, **kwargs))

        # Add connections to the simulation (fully connected)
        for idx, source in enumerate(self.sim.replicas):
            for target in self.sim.replicas[idx+1:]:
                self.sim.network.add_connection(source, target, True)

    def test_neighbors(self):
        """
        Test that the neighbor listing returns all neighbors.
        """
        self.build_neighbors()

        # Test the neighborhood
        for replica in self.sim.replicas:
            neighbors = list(replica.neighbors())
            self.assertEqual(len(neighbors), len(self.sim.replicas)-1)

    def test_neighbor_consistency_filter(self):
        """
        Test that the neighbors can be filtered on consistency.
        """

        self.build_neighbors()

        # Test the neighborhood filtering on a single consistency
        for replica in self.sim.replicas:
            neighbors = list(replica.neighbors(consistency=Consistency.STRONG))

            if replica.consistency == Consistency.STRONG:
                self.assertEqual(len(neighbors), 2)
            else:
                self.assertEqual(len(neighbors), 3)

            for neighbor in neighbors:
                self.assertEqual(neighbor.consistency, Consistency.STRONG)

        # Test the neighborhood filtering on multiple consistencies
        for replica in self.sim.replicas:
            consistencies = {Consistency.STRONG, Consistency.EVENTUAL}
            neighbors = list(replica.neighbors(consistency=consistencies))

            if replica.consistency in consistencies:
                self.assertEqual(len(neighbors), 6)
            else:
                self.assertEqual(len(neighbors), 7)

            for neighbor in neighbors:
                self.assertIn(neighbor.consistency, consistencies)

    def test_neighbor_consistency_exclusion_filter(self):
        """
        Test that the neighbors can be excluded by consistency.
        """

        self.build_neighbors()

        # Test the neighborhood filtering on a single consistency
        for replica in self.sim.replicas:
            neighbors = list(replica.neighbors(consistency=Consistency.STRONG, exclude=True))

            if replica.consistency != Consistency.STRONG:
                self.assertEqual(len(neighbors), 7)
            else:
                self.assertEqual(len(neighbors), 8)

            for neighbor in neighbors:
                self.assertNotEqual(neighbor.consistency, Consistency.STRONG)

        # Test the neighborhood filtering on multiple consistencies
        for replica in self.sim.replicas:
            consistencies = {Consistency.STRONG, Consistency.EVENTUAL}
            neighbors = list(replica.neighbors(consistency=consistencies, exclude=True))

            if replica.consistency not in consistencies:
                self.assertEqual(len(neighbors), 3)
            else:
                self.assertEqual(len(neighbors), 4)

            for neighbor in neighbors:
                self.assertNotIn(neighbor.consistency, consistencies)

    def test_neighbor_location_filter(self):
        """
        Test that the neighbors can be filtered on location.
        """

        self.build_neighbors()

        # Test the neighborhood filtering on a single location
        for replica in self.sim.replicas:
            neighbors = list(replica.neighbors(location=Location.ALPHA))

            if replica.location == Location.ALPHA:
                self.assertEqual(len(neighbors), 2)
            else:
                self.assertEqual(len(neighbors), 3)

            for neighbor in neighbors:
                self.assertEqual(neighbor.location, Location.ALPHA)

        # Test the neighborhood filtering on multiple locations
        for replica in self.sim.replicas:
            locations = {Location.ALPHA, Location.CHARLIE}
            neighbors = list(replica.neighbors(location=locations))

            if replica.location in locations:
                self.assertEqual(len(neighbors), 4)
            else:
                self.assertEqual(len(neighbors), 5)

            for neighbor in neighbors:
                self.assertIn(neighbor.location, locations)

    def test_neighbor_location_exclusion_filter(self):
        """
        Test that the neighbors can be excluded by location.
        """

        self.build_neighbors()

        # Test the neighborhood filtering on a single location
        for replica in self.sim.replicas:
            neighbors = list(replica.neighbors(location=Location.ALPHA, exclude=True))

            if replica.location != Location.ALPHA:
                self.assertEqual(len(neighbors), 7)
            else:
                self.assertEqual(len(neighbors), 8)

            for neighbor in neighbors:
                self.assertNotEqual(neighbor.location, Location.ALPHA)

        # Test the neighborhood filtering on multiple locations
        for replica in self.sim.replicas:
            locations = {Location.ALPHA, Location.CHARLIE}
            neighbors = list(replica.neighbors(location=locations, exclude=True))

            if replica.location not in locations:
                self.assertEqual(len(neighbors), 5)
            else:
                self.assertEqual(len(neighbors), 6)

            for neighbor in neighbors:
                self.assertNotIn(neighbor.location, locations)

    def test_neighbor_location_and_consistency_filter(self):
        """
        Test that the neighbors can be filtered on both location and consistency.
        """

        self.build_neighbors()

        # Test the neighborhood filtering on a single location
        for replica in self.sim.replicas:
            neighbors = list(replica.neighbors(location=Location.BRAVO, consistency=Consistency.STRONG))

            if replica.location == Location.BRAVO and replica.consistency == Consistency.STRONG:
                self.assertEqual(len(neighbors), 1)
            else:
                self.assertEqual(len(neighbors), 2)

            for neighbor in neighbors:
                self.assertEqual(neighbor.location, Location.BRAVO)
                self.assertEqual(neighbor.consistency, Consistency.STRONG)

        # Test the neighborhood filtering on multiple locations/consistencies
        for replica in self.sim.replicas:
            locations = {Location.ALPHA, Location.CHARLIE}
            consistencies = {Consistency.CAUSAL, Consistency.EVENTUAL}
            neighbors = list(replica.neighbors(location=locations, consistency=consistencies))

            if replica.location in locations and replica.consistency in consistencies:
                self.assertEqual(len(neighbors), 3)
            else:
                self.assertEqual(len(neighbors), 4)

            for neighbor in neighbors:
                self.assertIn(neighbor.location, locations)
                self.assertIn(neighbor.consistency, consistencies)

    def test_neighbor_location_and_consistency_exclusion_filter(self):
        """
        Test that the neighbors can be excluded by both location and consistency.
        """

        self.build_neighbors()

        # Test the neighborhood filtering on a single location
        for replica in self.sim.replicas:
            neighbors = list(replica.neighbors(location=Location.BRAVO, consistency=Consistency.STRONG, exclude=True))

            if replica.location != Location.BRAVO and replica.consistency != Consistency.STRONG:
                self.assertEqual(len(neighbors), 3)
            else:
                self.assertEqual(len(neighbors), 4)

            for neighbor in neighbors:
                self.assertNotEqual(neighbor.location, Location.BRAVO)
                self.assertNotEqual(neighbor.consistency, Consistency.STRONG)

        # Test the neighborhood filtering on multiple locations/consistencies
        for replica in self.sim.replicas:
            locations = {Location.ALPHA, Location.CHARLIE}
            consistencies = {Consistency.CAUSAL, Consistency.EVENTUAL}
            neighbors = list(replica.neighbors(location=locations, consistency=consistencies, exclude=True))

            if replica.location not in locations and replica.consistency not in consistencies:
                self.assertEqual(len(neighbors), 1)
            else:
                self.assertEqual(len(neighbors), 2)

            for neighbor in neighbors:
                self.assertNotIn(neighbor.location, locations)
                self.assertNotIn(neighbor.consistency, consistencies)
