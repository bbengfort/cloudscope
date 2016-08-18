# cloudscope.viz
# Helper functions for creating output vizualiations from simulations.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Dec 04 13:49:54 2015 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: viz.py [d0f0ca1] benjamin@bengfort.com $

"""
Helper functions for creating output vizualiations from simulations.
"""

##########################################################################
## Imports
##########################################################################

from operator import itemgetter
from collections import defaultdict
from cloudscope.config import settings
from peak.util.imports import lazyModule
from cloudscope.colors import ColorMap
from networkx.readwrite import json_graph

# Perform lazy loading of vizualiation libraries
nx  = lazyModule('networkx')
gt  = lazyModule('graph_tool.all')
sns = lazyModule('seaborn')
plt = lazyModule('matplotlib.pyplot')
np  = lazyModule('numpy')
pd  = lazyModule('pandas')

##########################################################################
## Helper Functions
##########################################################################

def configure(**kwargs):
    """
    Sets various configurations for Seaborn from the settings or arguments.
    """

    # Get configurations to do modifications on them.
    style   = kwargs.pop('style', settings.vizualization.style)
    context = kwargs.pop('context', settings.vizualization.context)
    palette = kwargs.pop('palette', settings.vizualization.palette)

    # Set the configurations on SNS
    sns.set_style(style)
    sns.set_context(context)
    sns.set_palette(palette)

    return kwargs


##########################################################################
## Seaborn Drawing Utilities
##########################################################################

def plot_kde(series, **kwargs):
    """
    Helper function to plot a density estimate of some distribution.
    """
    kwargs = configure(**kwargs)
    return sns.distplot(np.array(series), **kwargs)


def plot_time(series, **kwargs):
    """
    Helper function to plot a simple time series on an axis.
    """
    kwargs = configure(**kwargs)
    return sns.tsplot(np.array(series), **kwargs)


##########################################################################
## Traces Drawing Utilities
##########################################################################

def plot_workload(results, series='devices', **kwargs):
    """
    Helper function to make a timeline plot of reads/writes.
    If devices is True, plots timeline by device, else Objects.
    """
    kwargs  = configure(**kwargs)
    outpath = kwargs.pop('savefig', None)
    series  = {
        'devices': 0,
        'locations': 1,
        'objects': 2,
    }[series.lower()]

    read_color  = kwargs.pop('read_color', '#E20404')
    write_color = kwargs.pop('write_color', '#1E05D9')
    locations   = defaultdict(list)

    # Build the data from the read and write time series
    for key in ('read', 'write'):
        for item in results.results[key]:
            locations[item[series]].append(
                item + [key]
            )

    # Sort the data by timestamp
    for key in locations:
        locations[key].sort(key=itemgetter(0))

    # Create the visualization
    rx = []
    ry = []
    wx = []
    wy = []

    for idx, (key, lst) in enumerate(sorted(locations.items(), key=itemgetter(0), reverse=True)):
        for item in lst:
            if item[3] > 1000000: continue
            if item[-1] == 'read':
                rx.append(int(item[3]))
                ry.append(idx)
            else:
                wx.append(int(item[3]))
                wy.append(idx)

    fig = plt.figure(figsize=(14,4))
    plt.ylim((-1,len(locations)))
    plt.xlim((-1000, max(max(rx), max(wx))+1000))
    plt.yticks(range(len(locations)), sorted(locations.keys(), reverse=True))
    plt.scatter(rx, ry, color=read_color, label="reads", alpha=0.5, s=10)
    plt.scatter(wx, wy, color=write_color, label="writes", alpha=0.5, s=10)

    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    if outpath:
        return plt.savefig(outpath, format='svg', dpi=1200)

    return plt


def plot_message_traffic(messages):
    """
    Plots message traffic on a per-replica basis over time. Input data should
    be an iterable of tuples of the form:

        (replica, timestamp)

    Which (handily) is exactly what is output to the results object.
    """

    # Create data frame from results.
    columns = ['replica', 'timestamp', 'type', 'latency']
    tsize = pd.DataFrame([
        dict(zip(columns, message)) for message in messages
    ])

    # Aggregate messages into a single count by replica
    messages = tsize.groupby(['timestamp', 'replica']).agg(len).unstack('replica').fillna(0)

    # Plot the bar chart
    ax = messages.plot(figsize=(14, 6), kind='bar', stacked=True, colormap='nipy_spectral')

    # Configure the figure
    ax.set_ylabel('number of messages')
    ax.set_title('Message Counts by Replica over Time')
    return ax


##########################################################################
## Graph Drawing Utilities
##########################################################################

def draw_topology(topo, kind='graph_tool', **kwargs):
    """
    Draws a network graph from a topology with either graph tool or networkx.
    """

    draw_funcs = {
        'graph_tool': draw_graph_tool_topology,
        'gt': draw_graph_tool_topology,
        'networkx': draw_networkx_topology,
        'nx': draw_networkx_topology,
    }

    if kind not in draw_funcs:
        raise BadValue(
            "Unknown graph draw kind '{}' chose from one of {}".format(
                kind, ", ".join(draw_funcs.keys())
            )
        )

    return draw_funcs[kind](topo, **kwargs)


def draw_graph_tool_topology(topo, **kwargs):
    """
    Draws a network topology as loaded from a JSON file with graph tool.
    """
    from cloudscope.results.graph import get_prop_type
    G = gt.Graph(directed=True)

    # Construct the Graph properties
    for key, value in topo['meta'].items():
        tname, value, key = get_prop_type(value, key)
        prop = G.new_graph_property(tname)
        G.graph_properties[key] = prop
        G.graph_properties[key] = value

    # Add the node properties
    nprops = set()
    for node in topo['nodes']:
        for key, val in node.items():
            if key in nprops: continue

            tname, value, key = get_prop_type(val, key)
            prop = G.new_vertex_property(tname)
            G.vertex_properties[key] = prop

            nprops.add(key)

    # Add the edge properties
    eprops = set()
    for edge in topo['links']:
        for key, val in edge.items():
            if key in eprops: continue

            if key == 'latency':
                for name in ('latency_mean', 'latency_stddev', 'latency_weight'):
                    prop = G.new_edge_property('float')
                    G.edge_properties[name] = prop
                continue

            tname, value, key = get_prop_type(val, key)
            if key in {'source', 'target'}:
                tname = 'string'

            prop = G.new_edge_property(tname)
            G.edge_properties[key] = prop

            eprops.add(key)

    # Add the nodes
    vertices = {}
    for idx,node in enumerate(topo['nodes']):
        v = G.add_vertex()
        vertices[idx] = v

        # Set the vertex properties
        for key, value in node.items():
            G.vp[key][v] = value

    # Add the edges
    for edge in topo['links']:
        src = vertices[edge['source']]
        dst = vertices[edge['target']]
        e = G.add_edge(src, dst)

        for key, value in edge.items():
            if key == 'latency':
                G.ep['latency_mean'][e] = float(value[0])
                G.ep['latency_stddev'][e] = float(value[1])
                G.ep['latency_weight'][e] = 1.0 / float(value[0])
                continue

            if key in {'source', 'target'}:
                G.ep[key][e] = topo['nodes'][value]['id']
            else:
                G.ep[key][e] = value

    # Graph Drawing Time
    vlabel  = G.vp['id']
    vsize   = 60
    vcolor  = G.new_vertex_property('string')
    vcmap   = {
        'stentor': "#9b59b6",
        'federated': "#3498db",
        'unknown': "#95a5a6",
        'eventual': "#e74c3c",
        'tag': "#34495e",
        'strong': "#2ecc71",
    }
    for vertex in G.vertices():
        vcolor[vertex] = vcmap[G.vp['consistency'][vertex]]

    ecolor  = G.new_edge_property('string')
    ecmap   = ColorMap('paired', shuffle=False)
    for edge in G.edges():
        ecolor[edge] = ecmap(G.ep['area'][edge])

    elabel  = G.ep['connection']
    esize   = G.ep['latency_weight']
    eweight = G.ep['latency_weight']
    esize   = gt.prop_to_size(esize, mi=2, ma=5)
    pos = gt.arf_layout(G, weight=esize)

    gt.graph_draw(
        G, pos=pos,
        vertex_text=vlabel, vertex_size=vsize, vertex_font_weight=1,
        vertex_pen_width=1.3, vertex_fill_color=vcolor,
        edge_pen_width=esize, edge_color=ecolor, edge_text=elabel,
        output_size=(1200,1200), output="{}.png".format(topo['meta']['title']),
    )

def draw_networkx_topology(topo, layout='circular', **kwargs):
    """
    Draws a network topology as loaded from a JSON file with networkx.
    """
    G = json_graph.node_link_graph(topo)

    cmap = {
        'stentor': "#9b59b6",
        'federated': "#3498db",
        'unknown': "#95a5a6",
        'eventual': "#e74c3c",
        'tag': "#34495e",
        'strong': "#2ecc71",
    }

    lmap = {
        'constant': 'solid',
        'variable': 'dashed',
        'normal': 'dashdot',
    }

    draw = {
        'circular': nx.draw_circular,
        'random': nx.draw_random,
        'spectral': nx.draw_spectral,
        'spring': nx.draw_spring,
        'shell': nx.draw_shell,
        'graphviz': nx.draw_graphviz,
    }[layout]

    # Compute the colors and links for the topology
    colors = [cmap[n[1]['consistency']] for n in G.nodes(data=True)]
    links  = [lmap[n[2]['connection']] for n in G.edges(data=True)]

    return draw(
        G, with_labels=True, font_weight='bold',
        node_size=800, node_color=colors,
        style=links, edge_color='#333333'
    )
