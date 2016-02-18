# cloudscope.viz
# Helper functions for creating output vizualiations from simulations.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Dec 04 13:49:54 2015 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: viz.py [] benjamin@bengfort.com $

"""
Helper functions for creating output vizualiations from simulations.
"""

##########################################################################
## Imports
##########################################################################

import networkx as nx

from operator import itemgetter
from collections import defaultdict
from cloudscope.config import settings
from peak.util.imports import lazyModule

# Perform lazy loading of vizualiation libraries
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


def plot_workload(results, devices=False, **kwargs):
    """
    Helper function to make a timeline plot of reads/writes.
    If devices is True, plots timeline by device, else location.
    """
    kwargs  = configure(**kwargs)
    outpath = kwargs.pop('savefig', None)
    series  = 2 if devices else 1

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
    x = []
    y = []
    c = []

    for idx, (key, lst) in enumerate(locations.items()):
        for item in lst:
            x.append(item[0])
            y.append(idx)
            c.append(read_color if item[-1] == 'read' else write_color)

    plt.figure(figsize=(14,4))
    plt.ylim((-1,len(locations)))
    plt.xlim((-1000, max(item[-1][0] for item in locations.values())+1000))
    plt.yticks(range(len(locations)), locations.keys())
    plt.scatter(x, y, color=c, alpha=0.5, s=10)

    if outpath:
        return plt.savefig(outpath, format='svg', dpi=1200)

    return plt

##########################################################################
## NetworkX Drawing Utilities
##########################################################################

def draw_topology(G):
    """
    Draws a network topology as loaded from a JSON file.
    """
    cmap = {
        'strong': '#91cf60',
        'medium': '#ffffbf',
        'low': '#fc8d59',
    }

    lmap = {
        'constant': 'solid',
        'variable': 'dashed',
    }

    # Compute the colors and links for the topology
    colors = [cmap[n[1]['consistency']] for n in G.nodes(data=True)]
    links  = [lmap[n[2]['connection']] for n in G.edges(data=True)]

    return nx.draw_circular(
        G, with_labels=True, font_weight='bold',
        node_size=800, node_color=colors,
        style=links, edge_color='#333333'
    )
