# cloudscope.results.metrics
# Specialized metrics objects for recording results accurately
#
# Author:   Benjamin Bengfort <bbengfort@districtdatalabs.com>
# Created:  Mon Aug 22 16:10:44 2016 -0400
#
# Copyright (C) 2016 District Data Labs
# For license information, see LICENSE.txt
#
# ID: metrics.py [] benjamin@bengfort.com $

"""
Specialized metrics objects for recording results accurately
"""

##########################################################################
## Imports
##########################################################################

from collections import Counter
from collections import defaultdict
from cloudscope.config import settings
from cloudscope.utils.statistics import OnlineVariance

##########################################################################
## Module Constants
##########################################################################

# Message actions to track
SENT = "sent"
RECV = "recv"
DROP = "dropped"


##########################################################################
## Message Counting
##########################################################################

class MessageMetric(object):
    """
    A base class that computes metrics on a per network message basis.
    """

    @classmethod
    def deserialize(klass, data):
        """
        Message metrics must be deserializable!
        """
        raise NotImplementedError(
            "Subclasses must implement the deserialize class method."
        )

    def get_message_type(self, message):
        """
        Determines the message type from the value of the message.
        """
        # Get the base type of the message.
        mtype = message.value.__class__.__name__ if message.value else "None"

        # If we are aggregating heartbeats in addition to append entries:
        if settings.simulation.aggregate_heartbeats:

            # Check if we're actually an append entries or a heartbeat
            if mtype == 'AppendEntries':

                # Tag/Complex entries
                if isinstance(message.value.entries, dict):
                    if not any(message.value.entries.values()):
                        mtype = 'Heartbeat'

                # Raft/Standard entries
                if not message.value.entries:
                    mtype = 'Heartbeat'

        return mtype

    def update(self, message, **kwargs):
        """
        MessageMetric objects must have an update method that accepts messages
        """
        raise NotImplementedError(
            "Subclasses must implement the update method."
        )

    def serialize(self):
        """
        MessageMetric objects must have a serialize method to write to disk.
        """
        raise NotImplementedError(
            "Subclasses must implement the serialize method."
        )


class MessageCounter(MessageMetric):
    """
    Specialized class for counting messages on a per-replica basis by
    maintaining three internal data structures:

        - messages: action -> message type -> count
        - replicas: source -> message type -> count
        - received: target -> message type -> count

    Messages maintains an action (sent, recv, drop) relationship to the
    count of message types, whereas replicas maintains a sent by replica
    relationship to message types and their counts. Finally a received counter
    maintains a received by replica relationship to message types and their
    counts (which is a bit of a duplication of the LatencyDistribution).
    """

    @classmethod
    def deserialize(klass, data):
        """
        Inverse of the serialization operation, instantiates the class from
        the native Python types.
        """
        # Instantiate the empty class
        instance = klass()

        # For all the primary counter properties, fill in the value
        for key in ('messages', 'replicas', 'received'):
            # Get the blank attribute from the class
            attr = getattr(instance, key)

            # For every name  in the data for that item
            for name, counts in data.get(key, {}).items():
                for mtype, count in counts.items():
                    attr[name][mtype] = count

        return instance

    def __init__(self):
        self.messages = defaultdict(Counter) # Tracks the sent, recv, drop according to message type
        self.replicas = defaultdict(Counter) # Tracks the messages sent between replicas according to type
        self.received = defaultdict(Counter) # Tracks the messages received between replicas according to type

    def update(self, message, action, **kwargs):
        """
        Must update with both a message and an action.
        """
        mtype = self.get_message_type(message)
        self.messages[action][mtype] += 1

        if action == SENT:
            self.replicas[message.source.id][mtype] += 1

        if action == RECV:
            self.received[message.target.id][mtype] += 1

        return mtype

    def serialize(self):
        """
        Returns the counters as dictionary objects.
        """
        return {
            "messages": self.messages,
            "replicas": self.replicas,
            "received": self.received,
        }


class LatencyDistribution(MessageMetric):
    """
    Specialized class for counting latencies (delays) of messages recieved on
    a per-replica basis by maintaining an online measurements of a running
    sum, count, and sum of squares to compute online mean, variance, and
    standard deviation of message types via the following data structure:

        - messages: source --> target --> message type --> online variance

    The total message variance between source, target pairs can be computed
    by summing two online variance objects.
    """

    @classmethod
    def deserialize(klass, data):
        """
        Intantiates the complex messages data structure from data structured
        as the the return from the serialize method.
        """
        instance = klass()

        for source, targets in data.items():
            for target, mtypes in targets.items():
                for mtype, stats in mtypes.items():
                    stats = OnlineVariance.deserialize(stats)
                    instance.messages[source][target][mtype] = stats

        return instance

    def __init__(self):
        # Nested default dictionaries, the highest level contains source ids
        # as the key, followed by dictionaries of target ids, followed by
        # dictionaries of message types whose value is an online variance.
        self.messages = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(OnlineVariance)
            )
        )

    def update(self, message, **kwargs):
        """
        Track the message delay by type for the source/target pair.
        """
        delay = message.delay or 0.0

        mtype = self.get_message_type(message)
        self.messages[message.source.id][message.target.id][mtype].update(delay)

        return mtype

    def serialize(self):
        """
        Writes out the current state of the online variance properties
        """
        return self.messages
