# cloudscope.simulation.base
# Base functionality for a replica on a personal cloud storage system.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 06:05:58 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: base.py [c2eb7ed] benjamin@bengfort.com $

"""
Base functionality for a replica on a personal cloud storage system.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.dynamo import Sequence
from cloudscope.utils.enums import Enum
from cloudscope.utils.strings import decamelize
from cloudscope.replica.access import Read, Write
from cloudscope.results.metrics import SENT, RECV, DROP
from cloudscope.simulation.network import Node, Message
from cloudscope.exceptions import AccessError, NetworkError

##########################################################################
## Enumerations
##########################################################################

class Consistency(Enum):
    """
    Enumerates various consistency guarentees
    """

    STRONG   = "strong"    # In this case refers to Raft
    CAUSAL   = "causal"    # No implementation yet
    EVENTUAL = "eventual"  # By default, anti-entropy with last update wins
    STENTOR  = "stentor"   # Eventual with double the anti-entropy voice
    RAFT     = "raft"      # Specifically a Raft consensus group
    TAG      = "tag"       # Specifically a tag consensus group


RAFT_TYPES = (Consistency.STRONG.value, Consistency.RAFT.value)
EVENTUAL_TYPES = (Consistency.EVENTUAL.value, Consistency.STENTOR.value)


class Location(Enum):
    """
    Defines the location types in a personal cloud.
    """

    HOME    = "home"
    WORK    = "work"
    MOBILE  = "mobile"
    CLOUD   = "cloud"
    UNKNOWN = "unknown"

    # WAN Locations (Stub)
    DESCHUTES = "Deschutes, OR"
    KEENE     = "Keene, NH"
    LUBBOCK   = "Lubbock, TX"

    # WAN Site Locations (Stub)
    ALPHA   = "alpha"
    BRAVO   = "bravo"
    CHARLIE = "charlie"
    DELTA   = "delta"
    ECHO    = "echo"


class Device(Enum):
    """
    Defines the device/replica types in the cluster.
    """

    DESKTOP = "desktop"
    STORAGE = "storage"
    LAPTOP  = "laptop"
    TABLET  = "tablet"
    PHONE   = "smartphone"
    BACKUP  = "backup"


class State(Enum):
    """
    Defines the various states that replicas can be in.
    """

    # Basic states
    UNKNOWN   = 0
    LOADING   = 1
    ERRORED   = 2

    # Consensus states
    READY     = 3
    FOLLOWER  = 4 # Raft alias for ready
    CANDIDATE = 5 # Raft election
    TAGGING   = 6 # Tag consensus
    LEADER    = 7 # Raft leadership
    OWNER     = 8 # Tag ownership


class ReadPolicy(Enum):
    """
    Defines the types of read policies allowed by replicas.
    """

    LATEST = "latest"
    COMMIT = "commit"


##########################################################################
## Replica Functionality
##########################################################################

class Replica(Node):
    """
    A replica is a network node that implements version handling.
    """

    # Autoincrementing ID
    counter = Sequence()

    def __init__(self, sim, **kwargs):
        # Initialze Node
        super(Replica, self).__init__(sim.env)

        # Simulation Environment
        self.sim = sim

        # Replica Properties
        self.id    = kwargs.get('id', 'r{}'.format(self.counter.next()))
        self.type  = kwargs.get('type', settings.simulation.default_replica)
        self.label = kwargs.get('label', "{}-{}".format(self.type, self.id))
        self.state = kwargs.get('state', State.READY)
        self.location    = kwargs.get('location', 'unknown')
        self.consistency = Consistency.get(kwargs.get(
            'consistency', settings.simulation.default_consistency
        ))

    ######################################################################
    ## Properties
    ######################################################################

    @property
    def state(self):
        """
        Manages the state of the replica when set.
        """
        if not hasattr(self, '_state'):
            self._state = State.ERRORED
        return self._state

    @state.setter
    def state(self, state):
        """
        When setting the state, calls `on_state_change` so that replicas
        can modify their state machines accordingly. Note that the state is
        changed before this call, so replicas should inspect the new state.
        """
        state = State.get(state)
        self._state = state
        self.on_state_change()

    ######################################################################
    ## Core Methods (Replica API)
    ######################################################################

    def send(self, target, value):
        """
        Intermediate step towards Node.send (which handles simulation network)
        - this method logs information about the message, records metrics for
        results analysis, and does final preperatory work for sent messages.
        Simply logs that the message has been sent.
        """

        try:
            # Call the super method to queue the message on the network
            event   = super(Replica, self).send(target, value)
        except NetworkError:
            # Drop the message if the network connection is down
            return self.on_dropped_message(target, value)

        # Track total number of sent messages and get message type for logging.
        message = event.value
        mtype = self.sim.results.messages.update(message, SENT)

        # Debug logging of the message sent
        self.sim.logger.debug(
            "message {} sent at {} from {} to {}".format(
                mtype, self.env.now, message.source, message.target
            )
        )

        # Track time series of sent messages
        if settings.simulation.trace_messages:
            self.sim.results.update(
                SENT, (message.source.id, message.target.id, self.env.now, mtype)
            )

        return event

    def recv(self, event):
        """
        Intermediate step towards Node.recv (which handles simulation network)
        - this method logs information about the message, records metrics for
        results analysis, and detects and passes the message to the correct
        event handler for that RPC type.

        Subclasses should create methods of the form `on_[type]_rpc` where the
        type is the lowercase class name of the RPC named tuple. The recv method will
        route incomming messages to their correct RPC handler or raise an
        exception if it cannot find the access method.
        """
        try:
            # Get the unpacked message from the event.
            message = super(Replica, self).recv(event)
        except NetworkError:
            # Drop the message if the network connection is down
            return self.on_dropped_message(event.value.target, event.value.value)

        # Track total number of sent messages and get message type for logging.
        mtype = self.sim.results.messages.update(message, RECV)

        # Track the message delay statistics of all received messages
        self.sim.results.latencies.update(message)

        # Debug logging of the message recv
        self.sim.logger.debug(
            "protocol {!r} received by {} from {} ({}ms delayed)".format(
                mtype, message.target, message.source, message.delay
            )
        )

        # Track time series of recv messages
        if settings.simulation.trace_messages:
            self.sim.results.update(
                RECV, (message.target.id, message.source.id, self.env.now, mtype, message.delay)
            )

        # Dispatch the RPC to the correct handler
        return self.dispatch(message)

    def read(self, name, **kwargs):
        """
        Exposes the read API for every replica server and is one of the two
        primary methods of replica interaction.

        The read method expects the name of the object to read from and
        creates a Read event with meta information about the read. It is the
        responsibility of the subclasses to determine if the read is complete
        or not.

        Note that name can also be a Read event (in the case of remote reads
        that want to access identical read functionality on the replica). The
        read method will not create a new event, but will pass through the
        passed in Read event.

        This is in direct contrast to the old read method, where the replica
        did the work of logging and metrics - now this is all in the read
        event (when complete is triggered).
        """
        if not name:
            raise AccessError(
                "Must supply a name to read from the replica server"
            )

        return Read.create(name, self, **kwargs)

    def write(self, name, **kwargs):
        """
        Exposes the write API for every replica server and is the second of
        the two  primary methods of replica interaction.

        the write method exepcts the name of the object to write to and
        creates a Write event with meta informationa bout the write. It is
        the responsibility of sublcasses to perform the actual write on their
        local stores with replication.

        Note that name can also be a Write event and this method is in very
        different than the old write method (see details in read).

        This method will be adapted in the future to deal with write sizes,
        blocks, and other write meta information.
        """
        if not name:
            raise AccessError(
                "Must supply a name to write to the replica server"
            )

        return Write.create(name, self, **kwargs)

    def serialize(self):
        """
        Outputs a simple object representation of the state of the replica.
        """
        return dict([
            (attr, getattr(self, attr))
            for attr in (
                'id', 'type', 'label', 'location', 'consistency'
            )
        ])

    ######################################################################
    ## Helper Methods
    ######################################################################

    def dispatch(self, message):
        """
        Dispatches an RPC message to the correct handler. Because RPC message
        values are expected to be typed namedtuples, the dispatcher looks for
        a handler method on the replica named similar to:

            def on_[type]_rpc(self, message):
                pass

        Where [type] is the snake_case of the RPC class, for example, the
        AppendEntries handler would be named on_append_entries_rpc.

        The dispatch returns the result of the handler.
        """
        name = message.value.__class__.__name__
        handler = "on_{}_rpc".format(decamelize(name))

        # Check to see if the replica has the handler.
        if not hasattr(self, handler):
            NotImplementedError(
                "Handler for '{}' not implemented, add '{}' to {}".format(
                    name, handler, self.__class__
                )
            )

        # Get the handler, call on message and return.
        handler = getattr(self, handler)
        return handler(message)

    def neighbors(self, consistency=None, location=None, exclude=False):
        """
        Returns all nodes that are connected to the local node, filtering on
        either consistency of location. If neither consistency nor location
        are supplied, then this simply returns all of the neighboring nodes.

        If exclude is False, this returns any node that has the specified
        consistency or location. If exclude is True it returns any node that
        doesn't have the specified consistency or location.
        """
        neighbors = self.connections.keys()

        # Filter based on consistency level
        if consistency is not None:
            # Convert a single consistenty level or a string into a collection
            if isinstance(consistency, (Consistency, basestring)):
                consistency = [Consistency.get(consistency)]
            else:
                consistency = map(Consistency.get, consistency)

            # Convert the consistencies into a set for lookup
            consistency = frozenset(consistency)

            # Filter connections in that consistency level
            if exclude:
                is_neighbor = lambda r: r.consistency not in consistency
            else:
                is_neighbor = lambda r: r.consistency in consistency

            neighbors = filter(is_neighbor, neighbors)

        # Filter based on location
        if location is not None:
            # Convert a single location into a collection
            if isinstance(location, (Location, basestring)):
                location = [location]

            # Convert the locations into a set for lookup.
            location = frozenset(location)

            # Filter connections in that consistency level
            if exclude:
                is_neighbor = lambda r: r.location not in location
            else:
                is_neighbor = lambda r: r.location in location

            neighbors = filter(is_neighbor, neighbors)

        return neighbors

    ######################################################################
    ## Event Handlers
    ######################################################################

    def on_state_change(self):
        """
        Subclasses can call this to handle instance state. See the `state`
        property for more detail (this is called on set).
        """
        pass

    def on_dropped_message(self, target, value):
        """
        Called when there is a network error and a message that is being sent
        is dropped - subclasses can choose to retry the message or send to
        someone else. For now, we'll just record and log the drop.
        """
        # Create a dummy message
        dummy = Message(self, target, value, None)
        mtype = self.sim.results.messages.update(dummy, DROP)

        # Debug logging of the message dropped
        self.sim.logger.debug(
            "message {} dropped from {} to {} at {}".format(
                mtype, self, target, self.env.now
            )
        )

        # Track time series of dropped messages
        if settings.simulation.trace_messages:
            self.sim.results.update(
                DROP, (self.id, target.id, self.env.now, mtype)
            )

    ######################################################################
    ## Object data model
    ######################################################################

    def __str__(self):
        return "{} ({})".format(self.label, self.id)
