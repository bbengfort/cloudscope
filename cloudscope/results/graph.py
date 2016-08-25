# cloudscope.results.graph
# Utilities for visualizing the topology with communications results.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Jun 24 15:48:03 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: graph.py [] benjamin@bengfort.com $

"""
Utilities for visualizing the topology with communications results.
"""

##########################################################################
## Imports
##########################################################################

from .analysis import aggregator

from operator import add
from collections import defaultdict
from peak.util.imports import lazyModule
from cloudscope.exceptions import BadValue

# Perform lazy loading of vizualiation libraries
gt = lazyModule('graph_tool.all')
np = lazyModule('numpy')
nx = lazyModule('networkx')


##########################################################################
## Helper Functions
##########################################################################

def merge(dicts):
    """
    Creates a single dictionary from a list of dictionaries via update.
    """
    obj = {}
    for d in dicts:
        obj.update(d)
    return obj


def get_prop_type(value, key=None):
    """
    Performs typing and value conversion for the graph_tool PropertyMap class.
    """
    if isinstance(key, unicode):
        # Encode the key as ASCII
        key = key.encode('ascii', errors='replace')

    # Deal with the value
    if isinstance(value, bool):
        tname = 'bool'

    elif isinstance(value, int):
        tname = 'float'
        value = float(value)

    elif isinstance(value, float):
        tname = 'float'

    elif isinstance(value, unicode):
        tname = 'string'
        value = value.encode('ascii', errors='replace')

    elif isinstance(value, dict):
        tname = 'object'

    else:
        tname = 'string'
        value = str(value)

    return tname, value, key


##########################################################################
## Vertex/Edge Extraction
##########################################################################

def extract_nodes(results):
    """
    Rather than parse the graph from the topology, the graph is constructed
    from the results, inspecting actual communication rather than physical
    connections.

    Extract nodes grabs information about each node from the first element
    of every timeseries (expects a replica id in that position) and then
    aggregates the results as a properties on the nodes.

    This function returns a dictionary of node: properties.
    """

    # Parse the results series and divide by replica id
    nodes = defaultdict(lambda: defaultdict(list))
    for key, values in results.results.iteritems():
        for value in values:
            # Expecting the first item in every series to be the replica id
            nodes[value[0]][key].append(value)

    # Compute the aggregates for each series
    vertices = {
        node: merge([
            aggregator(key, values) for key, values in series.iteritems()
        ])
        for node, series in nodes.iteritems()
    }

    # Add the meta information from the topology
    for meta in results.topology['nodes']:
        vid = meta['id']
        for key, val in meta.items():
            vertices[vid][key] = val

    # Add the number of messages from the results
    sent = results.messages.replicas
    recv = results.messages.received

    for vid, msgs in sent.items():
        vertices[vid]['sent'] = sum(msgs.values())

    for vid, msgs in recv.items():
        vertices[vid]['recv'] = sum(msgs.values())

    return vertices


def extract_edges(results):
    """
    Rather than parse the graph from the topology, the graph is constructed
    from the results, inspecting actual communication rather than physical
    connections.

    Extract edges grabs information about how nodes are connected by
    inspecting the messages series.
    """

    # Get edge information from the results.latencies object
    # This is in the form source -> target -> message type -> statistics
    latencies = results.latencies
    messages = latencies if isinstance(latencies, dict) else latencies.messages
    edges = {}

    for source, conns in messages.items():
        for target, mtypes in conns.items():

            # Reduce all the message types into a single all messages edge.
            stats = reduce(add, mtypes.values())
            edges[(source, target)] = stats.serialize()

    # Add edge weights to the nodes
    count = sum(stats['samples'] for stats in edges.values())
    most  = max(stats['samples'] for stats in edges.values())

    for key in edges.keys():
        msgs = edges[key]['samples']
        edges[key]['weight'] = msgs / count
        edges[key]['norm']   = msgs / most
        edges[key]['count']  = msgs

    return edges


def extract_message_edges(results):
    """
    Rather than parse the graph from the topology, the graph is constructed
    from the results, inspecting actual communication rather than physical
    connections.

    Extract message edges grabs information about how nodes are connected by
    inspecting the `recv` series as in extract_edges. However, this function
    adds more edges by filtering on message type not just aggregating all
    total messages between nodes.
    """

    # Get edge information from the results.latencies object
    # This is in the form source -> target -> message type -> statistics
    latencies = results.latencies
    messages = latencies if isinstance(latencies, dict) else latencies.messages
    edges = {}

    for source, conns in messages.items():
        for target, mtypes in conns.items():
            for mtype, stats in mtypes.items():
                edges[(source, target, mtype)] = stats.serialize()

    # Add edge weights to the nodes
    count = sum(stats['samples'] for stats in edges.values())
    most  = max(stats['samples'] for stats in edges.values())

    for key in edges.keys():
        msgs = edges[key]['samples']
        edges[key]['weight'] = msgs / count
        edges[key]['norm']   = msgs / most
        edges[key]['count']  = msgs
        edges[key]['label']  = key[2]

    return edges


##########################################################################
## Graph Tool graph generation
##########################################################################

def extract_graph(results, kind='graph_tool', **kwargs):
    """
    Extracts a graph from the node and edge extractor from the results.
    Kind can be either graph_tool (gt) or networkx (nx), returns a directed
    graph of either type with properties annotated on the graph, nodes, edges.
    """

    extractors = {
        'graph_tool': extract_graph_tool_graph,
        'gt': extract_graph_tool_graph,
        'networkx': extract_networkx_graph,
        'nx': extract_networkx_graph,
    }

    if kind not in extractors:
        raise BadValue(
            "Unknown graph kind '{}' chose from one of {}".format(
                kind, ", ".join(extractors.keys())
            )
        )

    return extractors[kind](results, **kwargs)


def extract_graph_tool_graph(results, **kwargs):
    """
    Constructs a graph-tool Graph, which is not trivial.
    To get back to edge colors by type, create an inner function which only
    takes nodes and edges and allow the direct passing of nodes and edges
    in that function. This function will only generate the nodes and edges
    as normal and pass them through.
    """
    # Create the directed graph
    G = gt.Graph(directed=True)

    # Construct the Graph Properties
    graph = results.settings
    graph.update(results.topology['meta'])
    graph['name'] = "Communications Graph: {}".format(graph.get('title', 'CloudScope Simulation'))

    # Add the Graph Properties
    for key, value in graph.items():
        tname, value, key = get_prop_type(value, key)
        prop = G.new_graph_property(tname)
        G.graph_properties[key] = prop  # Set the PropertyMap
        G.graph_properties[key] = value # Set the actual value

    # Extract the nodes and the edges
    nodes = extract_nodes(results)

    if kwargs.get('by_message_type', False):
        edges = extract_message_edges(results)
    else:
        edges = extract_edges(results)

    # Add the node properties
    nprops = set() # cache to only add properties once
    for node, data in nodes.items():

        # Add the Node ID property
        prop = G.new_vertex_property('string')
        G.vertex_properties['id'] = prop

        for key, val in data.items():
            if key in nprops: continue

            tname, value, key = get_prop_type(val, key)
            prop = G.new_vertex_property(tname)
            G.vertex_properties[key] = prop

            nprops.add(key)

    # Add the edge properties
    eprops = set() # cache to only add properties once
    for edge, data in edges.items():

        # Add the sender edge property
        prop = G.new_edge_property('string')
        G.edge_properties['sender'] = prop

        # Add the receiver edge property
        prop = G.new_edge_property('string')
        G.edge_properties['receiver'] = prop

        for key, val in data.items():
            if key in eprops: continue

            tname, value, key = get_prop_type(val, key)
            prop = G.new_edge_property(tname)
            G.edge_properties[key] = prop

            eprops.add(key)

    # Add the nodes
    vertices = {} # vertex mapping for tracking later
    for node, data in nodes.items():
        # Create the vertex and annotate
        v = G.add_vertex()
        vertices[node] = v

        # Set the vertex properties
        data['id'] = node
        for key, value in data.items():
            G.vp[key][v] = value


    # Add the edges
    for edge, data in edges.items():
        src = vertices[edge[0]]
        dst = vertices[edge[1]]
        e = G.add_edge(src, dst)

        # Add edge properties
        data['sender'] = edge[0]
        data['receiver'] = edge[1]
        for key, value in data.items():
            G.ep[key][e] = value

    return G


def extract_networkx_graph(results, **kwargs):
    raise NotImplementedError("Not implemented quite yet.")
