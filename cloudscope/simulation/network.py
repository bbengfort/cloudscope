# cloudscope.simulation.network
# Implements the networking interface for the simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Jan 25 16:14:17 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: network.py [] benjamin@bengfort.com $

"""
Implements the networking interface for the simulation.

A Network is a collection of unidirectional Connections between objects that
are "connectable", e.g. they implement `send` and `recv` methods. Connections
maintain information between who and how two connectable objects communicate,
and the Network manages Messages -- events that are sent between them.
"""

##########################################################################
## Imports
##########################################################################

import random
import networkx as nx

from collections import defaultdict
from collections import namedtuple
from networkx.readwrite import json_graph

from cloudscope.config import settings
from cloudscope.exceptions import UnknownType
from cloudscope.simulation.base import Process


##########################################################################
## Module Constants
##########################################################################

CONSTANT = "constant"
VARIABLE = "variable"

Message  = namedtuple('Message', 'source, target, value')

##########################################################################
## A Node implements the connectible interface
##########################################################################

class Node(object):
    """
    A node is something that is "connectible", e.g. has a send and recv
    method as well as an optional broadcast mechanism. Subclasses of this
    node type do it through a reference to the primary network object.
    """

    def __init__(self):
        # The network is associated when being connected.
        self.network = None

    @property
    def connections(self):
        """
        Returns all current connections with the network
        """
        return self.network.connections[self]

    def send(self, target, value):
        """
        The send messsage interface required by connectible objects.
        """
        pass

    def recv(self, message):
        """
        The recv message interface required by connectible objects.
        """
        raise NotImplementedError("Subclasses must handle received messages.")

    def broadcast(self, value):
        """
        Sends a message to every connection on the network.
        """
        pass


##########################################################################
## Connection between two connectible objects.
##########################################################################

class Connection(object):
    """
    Create a constant or variable unidirectional connection between a source
    and a target "connectible" object. If constant, specify latency as an int
    otherwise specify the latency as a tuple.

    Connections are necessarily unidirectional so that a single replica can
    be "taken down" in the simulation, e.g. connections are deactivated to
    prevent communication; we want to do this without preventing communication
    in the other direction.
    """

    def __init__(self, network, source, target, **kwargs):
        self.network  = network
        self.source   = source
        self.target   = target
        self.type     = kwargs.get('connection', CONSTANT)
        self.active   = kwargs.get('active', True)

        # Set the latency protected variable
        self._latency = kwargs.get(
            'latency', settings.simulation.default_latency
        )

    def latency(self):
        """
        Computes the latency from the latency range.
        """
        # Constant Connections
        if self.type == CONSTANT:
            assert isinstance(self._latency, int)
            return self._latency

        # Variable Connections
        if self.type == VARIABLE:
            assert isinstance(self._latency, (tuple, list))
            return random.randint(*self._latency)

        # Something went wrong
        raise UnknownType(
            "Unkown connection type, {!r}".format(self.type)
        )

    def get_latency_range(self):
        """
        Returns the latency range no matter the type.
        """
        if self.type == CONSTANT:
            return (self._latency, self._latency)
        return self._latency

    def serialize(self):
        return {
            "connection": self.type,
            "active": self.active,
            "latency": self._latency,
        }

##########################################################################
## Network of connections
##########################################################################

class Network(object):
    """
    A Network is a collection of connectible objects that essentially
    represents a directed graph of communication. Bidirectional communications
    are the default and are added as two edges in the network graph.
    """

    def __init__(self):
        self.connections = defaultdict(dict)

    def add_connection(self, source, target, bidirectional=False, **kwargs):
        """
        Adds a connection object between two nodes and tracks it. If the
        bidirectional flag is True, a repeat call is made for target, source.
        """
        # Assign this network to the source
        source.network = self

        # Create and add the connection for the source
        conn = Connection(self, source, target, **kwargs)
        self.connections[source][target] = conn

        # Call again for a bidirectional connection
        if bidirectional:
            self.add_connection(target, source, **kwargs)

    def remove_connection(self, source, target, bidirectional=False):
        """
        Removes a connection between objects.
        """
        del self.connections[source][target]

        if bidirectional:
            self.remove_connection(target, source)

    def iter_connections(self):
        """
        Iterate through all the connection objects
        """
        for source, link in self.connections.iteritems():
            for connection in link.values():
                yield connection

    def filter(self, type):
        """
        Filter the connections by type, e.g. constant or variable.
        """
        for connection in self.iter_connections():
            if connection.type == type:
                yield connection

    def get_latency_ranges(self):
        """
        Computes the minimum and maximum latencies for all connection types.
        """
        latencies = defaultdict(set)
        for connection in self.iter_connections():
            for latency in connection.get_latency_range():
                latencies[connection.type].add(latency)

        return dict([
            (conn, (min(late), max(late)))
            for conn, late in latencies.iteritems()
        ])

    def graph(self):
        """
        Returns a NetworkX undirected graph of the network by first creating
        a directed graph then calling the NetworkX to_undirected method.
        """
        graph = nx.DiGraph()
        for source, links in self.connections.iteritems():
            graph.add_node(source.id, **source.serialize())

            for target, conn in links.iteritems():
                graph.add_edge(source.id, target.id, **conn.serialize())

        return graph.to_undirected()

    def serialize(self):
        """
        Returns the D3 JSON representation of the graph
        """
        graph = self.graph()
        return json_graph.node_link_data(graph)
