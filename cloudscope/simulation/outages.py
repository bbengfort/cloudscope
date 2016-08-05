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
from cloudscope.utils.timez import humanizedelta
from cloudscope.simulation.base import NamedProcess
from cloudscope.dynamo import BoundedNormal, Bernoulli
from cloudscope.utils.decorators import setter, memoized
from cloudscope.exceptions import BadValue, OutagesException
from cloudscope.simulation.network import WIDE_AREA, LOCAL_AREA

from collections import Sequence, defaultdict, namedtuple


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
        return OutageScript(outages, sim, **kwargs)

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
        self.do_outage = Bernoulli(kwargs.pop('outage_prob', settings.simulation.outage_prob))

        # NOTE: This will not call any methods on the connections (on purpose)
        self._state = ONLINE

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
            raise OutagesException(
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
        # If we were previously offline:
        if self.state == OUTAGE:
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
        # If we were previously online:
        if self.state == ONLINE:
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

            # Log (info) the outage/online state and duration
            self.sim.logger.info(
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
## Outages Collection
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
            raise OutagesException(
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


##########################################################################
## Outages Writer and Reader
##########################################################################

OutageEvent = namedtuple("OutageEvent", "timestep, state, source, target")

class OutagesWriter(object):
    """
    This object wraps an Outages collection of one or more OutageGenerator
    objects and writes the generated results to disk, which can be read by an
    OutagesReader object and replayed by a ScriptedOutages generator.
    """

    def __init__(self, outages, timesteps=None):
        """
        Initializes a writer with the outages collection and a maximum number
        of timesteps to write to each outages script file.
        """
        self.outages = outages
        self.timesteps = timesteps or settings.simulation.max_sim_time

    def write(self, fobj):
        """
        Writes out a complete script of outages to the passed in file-like
        object. Returns the number of rows written to the file.
        """
        for idx, outage in enumerate(self):
            fobj.write("{}\t{}\t{}\t{}\n".format(*outage))
        return idx + 1

    def __iter__(self):
        """
        Returns a generator that yields a complete script of outages.
        """

        timestep = 0
        schedule = defaultdict(list)
        states   = {}

        # Initialze the schedule and state tracking
        for generator in self.outages:
            states[generator] = generator.state
            schedule[int(generator.duration())].append(generator)

        # Iterate through time
        while timestep < self.timesteps:
            # Update the timestep to the next time in the schedule
            timestep = min(schedule.keys())

            # Determine outages for all scheduled workloads
            for generator in schedule.pop(timestep):
                # Update the state of the outage generator
                generator.update()

                # Reschedule the generator
                schedule[int(generator.duration()) + timestep].append(generator)

                # If the state not changed keep going otherwise update state
                if states[generator] == generator.state: continue
                states[generator] = generator.state

                # Yield outage events for each connection in the generator
                for conn in generator.connections:
                    yield OutageEvent(
                        timestep, generator.state, conn.source.id, conn.target.id
                    )


class OutagesReader(object):
    """
    A generator that parses and yields outage events from a TSV on disk.
    """

    def __init__(self, path):
        """
        Primary input is the location on disk of the outages script.
        """
        self.path = path

    def parse(self, line):
        """
        Parses and validates a line from an outages file.
        """
        # Parse the line, splitting on whitespace
        line = line.strip().split()

        # Validate the length
        if len(line) != 4:
            raise OutagesException(
                "Unparsable line: '{}'".format(" ".join(line))
            )

        # Validate the outage state
        if line[1] not in {OUTAGE, ONLINE}:
            raise OutagesException(
                "Unknown outage state '{}' must be {} or {}".format(
                    line[1], OUTAGE, ONLINE
                )
            )

        # Parse the timestep
        line[0] = int(float(line[0]))

        return OutageEvent(*line)

    def __iter__(self):
        """
        Reads the traces and yields the outage event tuple. Assumes a TSV
        file format structured as follows:

            timestep    state   source  target

        Where source and target are the replica ids and the state is online
        or offline (e.g. take the connection between source and target up or
        down at that particular timestep).
        """
        with open(self.path, 'r') as fobj:
            for line in fobj:
                yield self.parse(line)


##########################################################################
## OutageScript
##########################################################################

# TODO: Make a class hierarchy and extend this from the OutageGenerator base
class OutageScript(NamedProcess):
    """
    A deterministic method of providing outages and partitions through an
    outages script - a TSV file that contains the timestamp, state, and
    connection information (source, target) of the network links to manage.
    """

    def __init__(self, path, sim, **kwargs):
        self.sim     = sim                 # Hook to the simulation for logging
        self.path    = path                # path on disk to the outages script
        self.reader  = OutagesReader(path) # handle to the outages reader object
        self.clock   = 0                   # maintain time since last outage
        self.count   = 0                   # number of events in the script file
        self.network = sim.network         # get the connections between replicas
        self.connections = []              # track the connections managed by the script

        # Initialize the Process
        super(OutageScript, self).__init__(sim.env)

    @memoized
    def devices(self):
        """
        Mapping of replica IDs to deice for easy selection.
        """
        return {
            device.id: device for device in self.sim.replicas
        }

    def get_device(self, id):
        """
        Looks up a device by it's id.
        """
        if id not in self.devices:
            raise OutagesException(
                "Unkown device with replica id '{}'".format(id)
            )

        return self.devices[id]

    def get_connnection(self, src, dst):
        """
        Returns a connection object from two device ids, adding it to the list
        of managed connections if it is not already there.
        """
        source = self.get_device(src)
        target = self.get_device(dst)

        conn   = self.network.connections.get(source, {}).get(target, None)

        if conn is None:
            raise OutagesException(
                "No connection between {} and {}".format(source, target)
            )

        if conn not in self.connections:
            self.connections.append(conn)

        return conn

    def run(self):
        """
        Reads in outage events (must be ordered by timestep) and makes the
        connections specified either up or down according to the event state.
        """
        # Track how many connections have outage events together.
        local_count = 1

        # Read through the outage events in an ordered fashion.
        # Note this will only generate outages until they are exhaused.
        for event in self.reader:

            # Validate that the event occurs now or at the clock
            if event.timestep < self.clock:
                raise OutagesException(
                    "Unordered outage event '{}' occured at time {}".format(
                        event, self.clock
                    )
                )

            # Compute delay in simulation and timeout
            # If the delay is not zero then wait in simulation time.
            delay = event.timestep - self.clock
            if delay == 0:
                local_count += 1
            else:
                self.sim.logger.info(
                    "{} connections {} for {}".format(
                        local_count, event.state,
                        humanizedelta(milliseconds=delay)
                    )
                )
                local_count = 1
                yield self.env.timeout(delay)

            # Update our internal clock
            self.clock = self.env.now
            self.count += 1

            # Take the connection up or down depending on the event.
            conn = self.get_connnection(event.source, event.target)
            if event.state == ONLINE:
                conn.up()

            if event.state == OUTAGE:
                conn.down()

            self.sim.logger.debug(
                "{} is now {}".format(conn, event.state)
            )
