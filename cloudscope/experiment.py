# cloudscope.experiment
# Takes a topology as a template and generates experiments from it.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Feb 22 16:07:57 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: experiment.py [26c65a7] benjamin@bengfort.com $

"""
Takes a topology as a template and generates experiments from it.
"""

##########################################################################
## Imports
##########################################################################

import json
import collections

from copy import deepcopy
from cloudscope.dynamo import Uniform
from cloudscope.config import settings
from cloudscope.exceptions import CannotGenerateExperiments
from cloudscope.replica.base import Consistency

##########################################################################
## Helper Functions
##########################################################################

def spread(n, start, stop, width=None):
    """
    Given n slices, divide the range between start and stop; factored by
    width. E.g. if width is not given, just give the even n splits.

    If width is given, spread n width wide ranges over the start/stop with
    overlap or gaps depending on how n width wide ranges fits between.
    """

    if width is None:
        width = stop / n

    gap = (stop / n) - width

    for idx in xrange(n):
        yield [start, start + width]
        start += width + gap


def nested_update(d, u):
    """
    Updates a dictionary with other nested dictionaries.
    http://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    """
    for k,v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = nested_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def nested_randomize(d):
    """
    Expects a data structure of nested dictionaries whose leaf values are
    tuples that can be passed to a uniform random distribution.
    """
    r = deepcopy(d)
    for k,v in d.iteritems():
        if isinstance(v, dict):
            r[k] = nested_randomize(v)
        else:
            r[k] = Uniform(*v).get()
    return r


##########################################################################
## Experiment Generator
##########################################################################

class ExperimentGenerator(object):
    """
    A tool that generates experiments based off of specified dimensions.
    """

    @classmethod
    def load(klass, fobj, **kwargs):
        """
        Load the template from a JSON file on disk.
        """
        data = klass(json.load(fobj), **kwargs)

        # Convert consistencies to correct enum type
        for node in data.template['nodes']:
            node['consistency'] = Consistency.get(node['consistency'])

        return data

    def __init__(self, template, **options):
        self.template = template
        self.count    = options.pop('count', None)
        self.options  = self.get_defaults(options)

    def get_defaults(self, options):
        """
        Returns default options for the experiment generation, updating with
        the passed in options (must be a dictionary).
        """
        return nested_update({
            'users': {
                'minimum': 1,
                'maximum': 1,
                'step': 1,
            }
        }, options)

    def users(self):
        """
        Returns an iterator with the number of users as a dimension.
        """
        low  = self.options['users']['minimum']
        high = self.options['users']['maximum']
        step = self.options['users']['step']

        for num in xrange(low, high+1, step):
            yield num

    def generate(self, n=None):
        """
        Generates experiments based on n and the dimensions associated.
        """
        raise NotImplementedError(
            "Generate is specific to othe type of experiment generator!"
        )

    def jitter(self, n=1, **options):
        """
        Returns a generator of n copies of the current experiment generator,
        such that the options passsed in are randomized (all other options
        will remain fixed).

        The options passed into the jitter function should be a tuple which
        specifies the range of the random selection. A `Uniform` distribution
        is used, so either floats or integers can be used.

        Note: right now this is assume a single nested dictionary structure.
        """
        # Copy the options set on the generator
        defaults = deepcopy(self.options)
        defaults['count'] = self.count

        # Get the class of this experiment generator
        klass = self.__class__

        for idx in xrange(n):
            # Create a set of options that has been jittered
            jopts  = nested_randomize(options)
            kwargs = nested_update(defaults, jopts)
            yield klass(self.template, **kwargs)

    def __iter__(self):
        for experiment in self.generate():
            yield experiment

    def __len__(self):
        return sum(1 for experiment in self.generate())


##########################################################################
## Latency/User Generator
##########################################################################

class LatencyVariation(ExperimentGenerator):
    """
    This is the initial type of experiment generator whose primary variable
    dimension is latency. In addition, a number of users can also be added as
    a secondary dimensions (increasing the number of writes).
    """

    def get_defaults(self, options):
        """
        Update the ExperimentGenerator defaults with latency-specific stuff.
        """
        defaults = nested_update({
            'latency': {
                'minimum': 5,
                'maximum': 3000,
                'max_range': 1200,
            }
        }, options)

        return super(LatencyVariation, self).get_defaults(defaults)

    def latencies(self, n):
        """
        Returns a generator of (latency_range, mean_latency) pairs in a range
        over the minimum and maximum latencies, n times (with the spread func)
        """
        low   = self.options['latency']['minimum']
        high  = self.options['latency']['maximum']
        mrng  = self.options['latency']['max_range']

        width = min(mrng, (high / n))

        for latency in spread(n, low, high, width):
            mean = int(sum(map(float, latency)) / len(latency))
            yield latency, mean

    def generate(self, n=None):
        n = n or self.count
        if not n:
            raise CannotGenerateExperiments(
                "Must pass in a number of experiments to generate"
            )

        # Begin the experiment generation process.
        for n_users in self.users():
            for latency, mean_latency in self.latencies(n):
                # Create an experiment with n_user/latency dimensions
                experiment = deepcopy(self.template)

                # Update the nodes with latency-specific settings.
                for node in experiment['nodes']:
                    if node['consistency'] == Consistency.STRONG:
                        # Add raft-specific information
                        node['election_timeout']   = [
                            mean_latency * 10, mean_latency * 20
                        ]
                        node['heartbeat_interval'] = mean_latency * 5

                    if node['consistency'] == Consistency.MEDIUM:
                        # Add tagging-specific information
                        node['session_timeout'] = mean_latency * 20
                        node['heartbeat_interval'] = mean_latency * 5

                # Update the links with latency-specific settings.
                for link in experiment['links']:
                    if link['connection'] == 'variable':
                        link['latency'] = latency
                    else:
                        link['latency'] = mean_latency

                experiment['meta']['users'] = n_users

                yield experiment


class AntiEntropyVariation(LatencyVariation):
    """
    Generate experiments with variation in the anti-entropy delay.
    """

    def get_defaults(self, options):
        """
        Update the LatencyVariation defaults with anti-entropy options.
        """
        defaults = nested_update({
            'anti_entropy': {
                'minimum': settings.simulation.anti_entropy_delay,
                'maximum': settings.simulation.anti_entropy_delay,
            }
        }, options)

        return super(AntiEntropyVariation, self).get_defaults(defaults)

    def ae_delays(self, n):
        """
        Returns a generator of anti-entropy delays if a range is passed in.
        """
        low   = self.options['anti_entropy']['minimum']
        high  = self.options['anti_entropy']['maximum']

        if low == high:
            yield low
        else:
            for delay in spread(n, low, high):
                yield int(sum(map(float, delay)) / len(delay))

    def generate(self, n=None):
        n = n or self.count
        for experiment in super(AntiEntropyVariation, self).generate(n):
            for ae_delay in self.ae_delays(n):

                # Update the nodes with latency-specific settings.
                for node in experiment['nodes']:
                    if node['consistency'] == Consistency.LOW:
                        # Add eventual-specific information
                        node['anti_entropy_delay'] = ae_delay

                experiment['meta']['anti_entropy_delay'] = ae_delay
                yield experiment
