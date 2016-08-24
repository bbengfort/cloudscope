# cloudscope.results.base
# Manages the serialization of experimental results and their reporting.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sun Dec 06 21:00:52 2015 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: base.py [d0f0ca1] benjamin@bengfort.com $

"""
Manages the serialization of experimental results and their reporting.
"""

##########################################################################
## Imports
##########################################################################

import json
import cloudscope

from .report import details as report_details
from .report import topology as report_topology
from .metrics import MessageCounter
from .metrics import LatencyDistribution

from cloudscope.config import settings
from cloudscope.utils.serialize import JSONEncoder
from cloudscope.utils.decorators import Timer, memoized
from cloudscope.utils.timez import HUMAN_DATETIME
from cloudscope.utils.timez import epochptime
from cloudscope.viz import plot_workload

from collections import defaultdict

##########################################################################
## Results Object
##########################################################################

class Results(object):
    """
    A data stucture for managing results data.
    """

    @classmethod
    def load(klass, fp):
        """
        Load a results object from a JSON file on disk.
        """
        data = json.load(fp)
        return klass(**data)

    def __init__(self, **kwargs):
        # Set reasonable defaults for results
        self.results    = defaultdict(list)
        self.timer      = Timer()
        self.simulation = None
        self.version    = cloudscope.get_version()
        self.randseed   = settings.simulation.random_seed
        self.timesteps  = settings.simulation.max_sim_time
        self.settings   = dict(settings.simulation.options())
        self.messages   = MessageCounter()
        self.latencies  = LatencyDistribution()

        # Set any properties that need to be serialized (override above)
        for key, val in kwargs.iteritems():
            setattr(self, key, val)

    def update(self, key, value):
        """
        Updates the results by appending the value to the appropriate key.
        """
        self.results[key].append(value)

    def dump(self, fp, **kwargs):
        """
        Write the results object back down to disk.
        """
        kwargs['cls'] = kwargs.get('cls', JSONEncoder)
        json.dump(self, fp, **kwargs)

    def serialize(self):
        """
        Returns an iterator of key, value pairs of writeable properites.
        """

        def properties(self):
            for key, val in self.__dict__.iteritems():
                if not key.startswith('_') and not callable(val):
                    yield (key, val)

        return dict(properties(self))

    def plot(self, **kwargs):
        """
        Alias for cloudscope.viz.plot_results
        """
        raise NotImplementedError("Plotting the results not implemented yet.")

    def plot_workload(self, **kwargs):
        """
        Hook for cloudscope.viz.plot_workload
        """
        return plot_workload(self, **kwargs)

    @memoized
    def title(self):
        """
        Returns a pretty title for the results.
        """
        return '{} Simulation on {}'.format(
            self.simulation.rstrip('Simulation').rstrip(), self.finished.strftime(HUMAN_DATETIME)
        )

    @memoized
    def finished(self):
        """
        Returns the finished datetime from the timer.
        """
        finished = self.timer.finished if isinstance(self.timer, Timer) else self.timer['finished']
        return epochptime(finished)

    def print_details(self):
        return report_details(self)

    def print_topology(self):
        return report_topology(self)
