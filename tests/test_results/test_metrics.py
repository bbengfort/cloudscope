# tests.test_results.test_metrics
# Testing for the results metrics utilities.
#
# Author:   Benjamin Bengfort <bbengfort@districtdatalabs.com>
# Created:  Thu Aug 25 12:13:43 2016 -0400
#
# Copyright (C) 2016 District Data Labs
# For license information, see LICENSE.txt
#
# ID: test_metrics.py [] benjamin@bengfort.com $

"""
Testing for the results metrics utilities.
"""

##########################################################################
## Imports
##########################################################################

import json
import random
import unittest

from cloudscope.config import settings
from cloudscope.results.metrics import *
from cloudscope.simulation.network import Message
from cloudscope.utils.serialize import JSONEncoder
from cloudscope.utils.statistics import OnlineVariance
from collections import namedtuple, defaultdict, Counter
from cloudscope.replica.consensus.raft import AppendEntries

##########################################################################
## Message Classes and Constants
##########################################################################

Greeting  = namedtuple('Greeting', 'salutation, introduction')
Heartbeat = namedtuple('Heartbeat', 'timestamp, status')
Replica   = namedtuple('MockReplica', 'id')


def pack(msg, source='alpha', target='bravo', delay=None):
    """
    Helper method to pack a message for the message metric classes.
    """
    delay = delay or random.randint(5,100)
    return Message(source, target, msg, delay)


##########################################################################
## Base Message Metric Tests
##########################################################################

class MessageMetricTests(unittest.TestCase):
    """
    Tests the message metric base class and common methods.
    """

    def test_interface(self):
        """
        Assert message metric interface
        """

        # Must have a deserialize class method
        with self.assertRaises(NotImplementedError):
            MessageMetric.deserialize({})

        # Interface for instance methods
        instance = MessageMetric()

        # Must have an update method
        with self.assertRaises(NotImplementedError):
            message = pack(Greeting("Hello There!", "My name is Jean."))
            instance.update(message)

        # Must have an serialize method
        with self.assertRaises(NotImplementedError):
            instance.serialize()

    def test_get_message_type(self):
        """
        Test the simple get message type on message metric
        """

        instance = MessageMetric()
        message = pack(Greeting("Gutentag!", "Mah nameh est Amy."))
        mtype = instance.get_message_type(message)

        self.assertEqual(mtype, Greeting.__name__)

    def test_none_message_type(self):
        """
        Test null message values on get message type
        """
        instance = MessageMetric()
        message = pack(None)
        mtype = instance.get_message_type(message)

        self.assertEqual(mtype, "None")

    def test_aggregate_heartbeats(self):
        """
        Ensure that heartbeats are aggregated in message metric
        """
        # Set aggregate heartbeats to True
        prev = settings.simulation.aggregate_heartbeats
        settings.simulation.aggregate_heartbeats = True

        term = 1
        leaderId = 'r8'
        prevLogIndex = 42
        prevLogTerm  = 1
        leaderCommit = 38

        instance = MessageMetric()
        simple_entries  = ['a', 'b', 'c', 'd']
        complex_entries = {'a': [1, 2, 3], 'b': [3,4,5], 'c':[5,7,8]}
        simple_no_entries  = []
        complex_no_entries =  {'a': None, 'b': None, 'c': None}

        # Helper function to make append entires messages
        mkmsg = lambda entries: pack(AppendEntries(term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit))

        # Cases for testing
        cases = (
            (mkmsg(simple_entries), AppendEntries.__name__),
            (mkmsg(complex_entries), AppendEntries.__name__),
            (mkmsg(simple_no_entries), Heartbeat.__name__),
            (mkmsg(complex_no_entries), Heartbeat.__name__),
        )

        for msg, expected in cases:
            self.assertEqual(instance.get_message_type(msg), expected)

        # Return aggregate heartbeats to original state
        settings.simulation.aggregate_heartbeats = prev

    def test_no_aggregate_heartbeats(self):
        """
        Ensure that heartbeats are not aggregated in message metric
        """
        # Set aggregate heartbeats to True
        prev = settings.simulation.aggregate_heartbeats
        settings.simulation.aggregate_heartbeats = False

        term = 1
        leaderId = 'r8'
        prevLogIndex = 42
        prevLogTerm  = 1
        leaderCommit = 38

        instance = MessageMetric()
        simple_entries  = ['a', 'b', 'c', 'd']
        complex_entries = {'a': [1, 2, 3], 'b': [3,4,5], 'c':[5,7,8]}
        simple_no_entries  = []
        complex_no_entries =  {'a': None, 'b': None, 'c': None}

        # Helper function to make append entires messages
        mkmsg = lambda entries: pack(AppendEntries(term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit))

        # Cases for testing
        cases = (
            (mkmsg(simple_entries), AppendEntries.__name__),
            (mkmsg(complex_entries), AppendEntries.__name__),
            (mkmsg(simple_no_entries), AppendEntries.__name__),
            (mkmsg(complex_no_entries), AppendEntries.__name__),
        )

        for msg, expected in cases:
            self.assertEqual(instance.get_message_type(msg), expected)

        # Return aggregate heartbeats to original state
        settings.simulation.aggregate_heartbeats = prev


##########################################################################
## Message Counter Tests
##########################################################################

class MessageCounterTests(unittest.TestCase):

    def test_update(self):
        """
        Test message counting on receipt of a message
        """
        a1 = Replica('a1')
        b3 = Replica('b3')

        counter = MessageCounter()
        self.assertEqual(counter.messages, {})
        self.assertEqual(counter.replicas, {})
        self.assertEqual(counter.received, {})

        # Add a greeting message sent from a1 to b3
        msg1 = pack(Greeting("Hola", "meet Joe"), a1, b3)
        counter.update(msg1, SENT)
        self.assertEqual(counter.messages, {SENT:{Greeting.__name__: 1}})
        self.assertEqual(counter.replicas, {'a1':{Greeting.__name__: 1}})
        self.assertEqual(counter.received, {})

        # Add a greeting message sent from b3 to a1
        msg2 = pack(Greeting("Hola", "meet Joe"), b3, a1)
        counter.update(msg2, SENT)
        self.assertEqual(counter.messages, {SENT:{Greeting.__name__: 2}})
        self.assertEqual(counter.replicas, {'a1':{Greeting.__name__: 1}, 'b3':{Greeting.__name__: 1}})
        self.assertEqual(counter.received, {})

        # Add the receipt of the message from a1 to b3
        counter.update(msg1, RECV)
        self.assertEqual(counter.messages, {SENT:{Greeting.__name__: 2}, RECV:{Greeting.__name__: 1}})
        self.assertEqual(counter.replicas, {'a1':{Greeting.__name__: 1}, 'b3':{Greeting.__name__: 1}})
        self.assertEqual(counter.received, {'b3':{Greeting.__name__: 1}})

        # Add the drop of the message from b3 to a1
        counter.update(msg2, DROP)
        self.assertEqual(counter.messages, {SENT:{Greeting.__name__: 2}, RECV:{Greeting.__name__: 1}, DROP:{Greeting.__name__: 1}})
        self.assertEqual(counter.replicas, {'a1':{Greeting.__name__: 1}, 'b3':{Greeting.__name__: 1}})
        self.assertEqual(counter.received, {'b3':{Greeting.__name__: 1}})

    def test_serialization(self):
        """
        Test message counter serialization and deserialization
        """
        a1 = Replica('a1')
        b3 = Replica('b3')

        counter = MessageCounter()
        msg1 = pack(Greeting("Hola", "meet Joe"), a1, b3)
        msg2 = pack(Greeting("Hola", "meet Joe"), b3, a1)
        counter.update(msg1, SENT)
        counter.update(msg2, SENT)
        counter.update(msg1, RECV)
        counter.update(msg2, DROP)

        # Serialize the Data
        data = json.loads(json.dumps(counter, cls=JSONEncoder))

        self.assertEqual(data, {
            "messages": {SENT:{Greeting.__name__: 2}, RECV:{Greeting.__name__: 1}, DROP:{Greeting.__name__: 1}},
            "replicas": {'a1':{Greeting.__name__: 1}, 'b3':{Greeting.__name__: 1}},
            "received": {'b3':{Greeting.__name__: 1}},
        })

        # Deserialize the data
        instance = MessageCounter.deserialize(data)
        self.assertEqual(instance.messages, {SENT:{Greeting.__name__: 2}, RECV:{Greeting.__name__: 1}, DROP:{Greeting.__name__: 1}})
        self.assertEqual(instance.replicas, {'a1':{Greeting.__name__: 1}, 'b3':{Greeting.__name__: 1}})
        self.assertEqual(instance.received, {'b3':{Greeting.__name__: 1}})

        for metric in (instance.messages, instance.replicas, instance.received):
            self.assertIsInstance(metric, defaultdict)
            for value in metric.values():
                self.assertIsInstance(value, Counter)


##########################################################################
## Latency Distribution Tests
##########################################################################

class LatencyDistributionTests(unittest.TestCase):

    def test_update(self):
        """
        Test latency distribution update on receipt of a message
        """

        c4 = Replica('c4')
        e1 = Replica('e1')

        dist = LatencyDistribution()
        self.assertEqual(dist.messages, {})

        # Add a greeting message sent from e1 to c4 with 10ms latency
        msg1 = pack(Greeting("Bonjour", "Larry"), e1, c4, 10)
        dist.update(msg1)
        self.assertEqual(dist.messages, {'e1': {'c4': {'Greeting': OnlineVariance([10])}}})

        # Add a greeting message sent from e1 to c4 with 20ms latency
        msg2 = pack(Greeting("Hello", "Larry"), e1, c4, 20)
        dist.update(msg2)
        self.assertEqual(dist.messages, {'e1': {'c4': {'Greeting': OnlineVariance([10, 20])}}})

        # Add a greeting message sent from c4 to e1 with 10ms latency
        msg3 = pack(Greeting("Hola", "James"), c4, e1, 10)
        dist.update(msg3)
        self.assertEqual(dist.messages, {'e1': {'c4': {'Greeting': OnlineVariance([10, 20])}}, 'c4': {'e1': {'Greeting': OnlineVariance([10])}}})

        # Add a greeting message sent from c4 to e1 with 30ms latency
        msg4 = pack(Greeting("Hola", "James"), c4, e1, 30)
        dist.update(msg4)
        self.assertEqual(dist.messages, {'e1': {'c4': {'Greeting': OnlineVariance([10, 20])}}, 'c4': {'e1': {'Greeting': OnlineVariance([10, 30])}}})

    def test_update_no_latency(self):
        """
        Test that samples increases even with messages of no latency.
        """
        # Replicas
        c4 = Replica('c4')
        e1 = Replica('e1')

        # Messages (at least two samples for stats)
        msg1 = pack(Greeting("Bonjour", "Larry"), e1, c4, 10)
        msg2 = pack(Greeting("Bonjour", "Larry"), e1, c4, 10)

        dist = LatencyDistribution()
        dist.update(msg1)
        dist.update(msg2)

        # Initialization verification
        self.assertIn(e1.id, dist.messages)
        self.assertIn(c4.id, dist.messages[e1.id])
        self.assertIn(Greeting.__name__, dist.messages[e1.id][c4.id])

        stats = dist.messages[e1.id][c4.id][Greeting.__name__]

        # Test the statistics prior to null delay
        self.assertEqual(stats.samples, 2)
        self.assertEqual(stats.total, 20)
        self.assertEqual(stats.squares, 200)
        self.assertEqual(stats.mean, 10)
        self.assertEqual(stats.std, 0.0)
        self.assertEqual(stats.var, 0.0)

        # Add the null latency message
        # Yep, this line is what we've done all this work for ...
        msg = Message(e1, c4, Greeting("Bonjour", "Larry"), None)
        dist.update(msg)

        # Test the statistics after null delay
        self.assertEqual(stats.samples, 3)
        self.assertEqual(stats.total, 20)
        self.assertEqual(stats.squares, 200)
        self.assertEqual(stats.mean, 6.666666666666667)
        self.assertEqual(stats.std, 5.773502691896258)
        self.assertEqual(stats.var, 33.333333333333336)


    def test_serialization(self):
        """
        Test latency distribution serialization and deserialization
        """

        c4 = Replica('c4')
        e1 = Replica('e1')

        msg1 = pack(Greeting("Bonjour", "Larry"), e1, c4, 10)
        msg2 = pack(Greeting("Hello", "Larry"), e1, c4, 20)
        msg3 = pack(Greeting("Hola", "James"), c4, e1, 10)
        msg4 = pack(Greeting("Hola", "James"), c4, e1, 30)

        dist = LatencyDistribution()
        for msg in (msg1, msg2, msg3, msg4):
            dist.update(msg)

        data = json.loads(json.dumps(dist, cls=JSONEncoder))
        newdist = LatencyDistribution.deserialize(data)
        self.assertEqual(newdist.messages, {'e1': {'c4': {'Greeting': OnlineVariance([10, 20])}}, 'c4': {'e1': {'Greeting': OnlineVariance([10, 30])}}})
