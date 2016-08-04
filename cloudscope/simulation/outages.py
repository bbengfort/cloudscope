# cloudscope.simulation.outages
# Generate and replay outages in the network, similar to workload traces.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Aug 03 15:35:27 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: outages.py [] benjamin@bengfort.com $

"""
Generate and replay outages in the network, similar to workload traces.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.utils.decorators import setter
from cloudscope.dynamo import BoundedNormal, Bernoulli
from cloudscope.simulation.base import NamedProcess
from cloudscope.utils.timez import humanizedelta
from cloudscope.exceptions import BadValue
from cloudscope.simulation.network import WIDE_AREA, LOCAL_AREA

from collections import Sequence, defaultdict


##########################################################################
## Module Constants
##########################################################################

## Connection Outage Types
WIDE_OUTAGE   = "wide"
LOCAL_OUTAGE  = "local"
NODE_OUTAGE   = "node"
LEADER_OUTAGE = "leader"
BOTH_OUTAGE   = "both"

## All Partition Across Types
PARTITION_TYPES = (
    WIDE_OUTAGE, LOCAL_OUTAGE, NODE_OUTAGE, LEADER_OUTAGE, BOTH_OUTAGE,
)

## Connection States
ONLINE = "online"
OUTAGE = "offline"

##########################################################################
## Factory method to create the outages process
##########################################################################

def create(sim, **kwargs):
    """
    Returns the correct outages generator process(s) for the simulation.
    Similar to workload there are several possible outages to return depending
    on the arguments passed to the factory:

        - Load the outages from an outages file
        - Create a collection of outages based on the partition type.
        - Create latency variation vs. complete outages.

    See the Outages objects for more information.
    """
    # Create an outages reader process if passed in.
    outages = kwargs.pop('outages', None)
    if outages:
        raise NotImplementedError(
            "Outage trace not implemented yet!"
        )

    # Otherwise construct outages genrator processes
    return Outages(sim, **kwargs)


##########################################################################
## Outage Generator Process
##########################################################################

class OutageGenerator(NamedProcess):
    """
    A process that causes outages to occur across the wide or local area or
    across both areas, or to occur for leaders only. Outages are generated on
    a collection of connections, usually collected together based on the
    connection type. The outages script is run as follows in the simulation:

        - determine the probability of online vs. outage
        - use the normal distribution of online/outage to determine duration
        - cause outage if outage, wait until duration is over.
        - repeat from the first step.

    Outages can also do more than cut the connection, they can also vary the
    latency for that connection by changing the network parameters.
    """

    def __init__(self, sim, connections, **kwargs):
        """
        Initialize the workload with the simulation (containing both the
        environment and the topology for work), the set of connections to
        cause outages for as a group, and any additional arguments.
        """

        self.sim = sim
        self.connections = connections
        self.state = ONLINE # Must be set after connections!
        self.do_outage = Bernoulli(kwargs.pop('outage_prob', settings.simulation.outage_prob))

        # Distribution of outage duration
        self.outage_duration = BoundedNormal(
            kwargs.pop('outage_mean', settings.simulation.outage_mean),
            kwargs.pop('outage_stddev', settings.simulation.outage_stddev),
            floor = 10.0,
        )

        # Distribution of online duration
        self.online_duration = BoundedNormal(
            kwargs.pop('online_mean', settings.simulation.online_mean),
            kwargs.pop('online_stddev', settings.simulation.online_stddev),
            floor = 10.0,
        )

        # Initialize the Process
        super(OutageGenerator, self).__init__(sim.env)

    @setter
    def connections(self, value):
        """
        Allows passing a single connection instance or multiple.
        """
        if not isinstance(value, (tuple, list)):
            value = (value,)
        return tuple(value)

    @setter
    def state(self, state):
        """
        When the state is set on the outage generator, update connections.
        """
        if state == ONLINE:
            self.update_online_state()

        elif state == OUTAGE:
            self.update_outage_state()

        else:
            raise BadValue(
                "Unknown state: '{}' set either {} or {}".format(
                    state, ONLINE, OUTAGE
                )
            )

        return state

    def update_online_state(self):
        """
        Sets the state of the generator to online.
        NOTE - should not be called by clients but can be subclassed!
        """
        for conn in self.connections:
            conn.up()
            self.sim.logger.debug(
                "{} is now online".format(conn)
            )

    def update_outage_state(self):
        """
        Sets the state of the generator to outage.
        NOTE - should not be called by clients but can be subclassed!
        """
        for conn in self.connections:
            conn.down()
            self.sim.logger.debug(
                "{} is now offline".format(conn)
            )

    def duration(self):
        """
        Returns the duration of the current state in milliseconds.
        """
        if self.state == ONLINE:
            return self.online_duration.get()

        if self.state == OUTAGE:
            return self.outage_duration.get()

    def update(self):
        """
        Updates the state of the connections according to the outage
        probability. This method should be called routinely according to the
        outage and online duration distributions.
        """

        if self.do_outage.get():
            self.state = OUTAGE
        else:
            self.state = ONLINE

    def run(self):
        """
        The action that generates outages on the passed in set of connections.
        """
        while True:

            # Get the duration of the current state
            duration = self.duration()

            # Log (debug) the outage/online state and duration
            self.sim.logger.warn(
                "{} connections {} for {}".format(
                    len(self.connections), self.state,
                    humanizedelta(milliseconds=duration)
                )
            )

            # Wait for the duration
            yield self.env.timeout(duration)

            # Update the state of the outage
            self.update()

    def __str__(self):
        """
        String representation of the outage generator.
        """
        return "{}: {} connections {}".format(
            self.name, len(self.connections), self.state
        )


##########################################################################
## Outages
##########################################################################

class Outages(Sequence):
    """
    A collection of outage generators that knows how to allocate or coordinate
    a set of connections to be taken down or made online together.
    """

    outage_generator_class = OutageGenerator

    def __init__(self, sim, partition_across=None, **kwargs):
        """
        Pass in a network and an outage type as well as outage specific args,
        and a set of outage generators will be created for specific groups of
        internal connections according to the outage type.
        """

        # Add the outages parameters
        self.sim               = sim
        self.network           = sim.network
        self.outage_kwargs     = kwargs

        # Internal collection
        self.outage_generators = ()

        # Generate outage generators
        self.allocate(partition_across or settings.simulation.partition_across)

    def allocate(self, partition_across=WIDE_OUTAGE):
        """
        Allocates the internal outage generators for the network.
        """

        # Check the outage types strategy
        if partition_across not in PARTITION_TYPES:
            raise BadValue(
                "'{}' is not a valid outage type.".format(partition_across)
            )

        # Set the outage type for reference.
        self.partition_across   = partition_across

        # Choose the correct allocation mechansim
        allocate_method = {
            WIDE_OUTAGE: self._allocate_wide,
            LOCAL_OUTAGE: self._allocate_local,
            BOTH_OUTAGE: self._allocate_both,
            NODE_OUTAGE: self._allocate_node,
            LEADER_OUTAGE: self._allocate_leader,
        }[self.partition_across]

        # Call the allocate method
        self.outage_generators = tuple(allocate_method())

    def _allocate_wide(self):
        """
        Internal allocation method for the wide strategy.

        Each outage generator works on a collection of outbound connections
        from a single location. Allocates an outage generator for each
        location in the network, filtering out local connections.
        """
        locations = defaultdict(list)
        for connection in self.network.iter_connections():
            if connection.area == WIDE_AREA:
                locations[connection.source.location].append(connection)

        for connections in locations.values():
            yield self.outage_generator_class(
                self.sim, connections, **self.outage_kwargs
            )

    def _allocate_local(self):
        """
        Internal allocation method for the local strategy.
        """
        locations = defaultdict(list)
        for connection in self.network.iter_connections():
            if connection.area == LOCAL_AREA:
                locations[connection.source.location].append(connection)

        for connections in locations.values():
            yield self.outage_generator_class(
                self.sim, connections, **self.outage_kwargs
            )

    def _allocate_both(self):
        """
        Internal allocation method for the both strategy.
        """
        for generator in self._allocate_wide():
            yield generator

        for generator in self._allocate_local():
            yield generator

    def _allocate_node(self):
        """
        Internal allocation method for the node strategy: e.g. take down all
        connections for a single node at a time.
        """
        for node, links in self.network.connections.items():
            yield self.outage_generator_class(
                self.sim, links.values(), **self.outage_kwargs
            )

    def _allocate_leader(self):
        """
        Internal allocation method for the leader strategy.
        """
        raise NotImplementedError(
            "{} outage allocation strategy not implemented yet.".format(
                self.partition_across
            )
        )

    def __getitem__(self, idx):
        return self.outage_generators[idx]

    def __len__(self):
        return len(self.outage_generators)
