# cloudscope.results.report
# Text based reporting tools for quick information on a results file.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Jun 24 07:53:26 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: report.py [5afcfab] benjamin@bengfort.com $

"""
Text based reporting tools for quick information on a results file.
"""

##########################################################################
## Imports
##########################################################################

from copy import deepcopy
from operator import itemgetter

from cloudscope.exceptions import BadValue
from cloudscope.utils.strings import title_snaked
from cloudscope.utils.timez import epochptime


##########################################################################
## Reports for a single results object
##########################################################################

def details(results):
    """
    Returns a string with text formated details about the report.
    """

    if isinstance(results, (list, tuple)):
        raise BadValue(
            "This report function works only on a single results object"
        )

    banner = (
        "Simulation: {} (Cloudscope v{})\n"
        "{}\n\n"
        "Ran on: {} ({})\n\n"
        "Settings\n"
        "========\n"
    ).format(
        results.simulation, results.version, results.topology['meta']['description'],
        epochptime(results.timer['started']).strftime('%b %d, %Y at %H:%M %Z'),
        results.timer['elapsed'],
        results.randseed,
    )

    longest = max(len(key) for key in results.settings)
    frmt = "{{: <{0}}} {{: >12}}".format(longest)


    return banner + "\n".join([
        frmt.format(title_snaked(key), value)
        for key, value in results.settings.items()
    ])


def topology(results):
    """
    Returns a string with a text formatted description of the topology
    """

    if isinstance(results, (list, tuple)):
        raise BadValue(
            "This report function works only on a single results object"
        )

    topology = deepcopy(results.topology)
    nodes = topology['nodes']
    links = topology['links']

    for link in links:
        latency = link['latency']
        if link['connection'] == 'constant':
            # Convert the latency into a list
            latency = [latency]

        for rid in ('source', 'target'):
            node = nodes[link[rid]]

            if 'minlat' not in node:
                node['minlat'] = latency[0]
            else:

                node['minlat'] = min(node['minlat'], latency[0])

            if 'maxlat' not in node:
                node['maxlat'] = latency[-1]
            else:
                node['maxlat'] = max(node['maxlat'], latency[-1])

    output = []
    for node in sorted(nodes, key=itemgetter('id')):
        output.append(
            "{}: {} ({}, {}) {}-{}ms connection".format(
                node['id'], node['label'], node['location'],
                node['consistency'], node['minlat'], node['maxlat']
            )
        )
    return "\n".join(output)


##########################################################################
## Reports for multiple results objects
##########################################################################
