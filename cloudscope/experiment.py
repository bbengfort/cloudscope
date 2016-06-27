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
from cloudscope.exceptions import BadValue
from cloudscope.exceptions import CannotGenerateExperiments
from cloudscope.replica.base import Consistency
from cloudscope.simulation.network import CONSTANT, VARIABLE, NORMAL


## Area constants
LOCAL_AREA = "local"
WIDE_AREA  = "wide"


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

        # Width specifies how to spread mean latencies and also the stddev
        width  = min(mrng, (high / n))

        for latency in spread(n, low, high, width):
            mean = int(sum(map(float, latency)) / len(latency))
            stddev = (float(latency[1] - mean) / 2.5)
            yield {
                'latency_range': latency,
                'latency_mean': mean,
                'latency_stddev': stddev,
            }

    def generate(self, n=None):
        n = n or self.count
        if not n:
            raise CannotGenerateExperiments(
                "Must pass in a number of experiments to generate"
            )

        # Begin the experiment generation process.
        for n_users in self.users():
            for latency_kwargs in self.latencies(n):
                # Create an experiment with n_user/latency dimensions
                experiment = deepcopy(self.template)

                # Update the nodes with latency-specific settings.
                for node in experiment['nodes']:
                    self.update_node_params(node, **latency_kwargs)


                # Update the links with latency-specific settings.
                for link in experiment['links']:
                    self.update_link_params(link, **latency_kwargs)

                # Update the experiment with meta information
                self.update_experiment_meta(experiment, users=n_users, **latency_kwargs)

                # Yield the current experiment
                yield experiment

    def update_node_params(self, node, **kwargs):
        """
        In place update of the node in the JSON structure according to the
        parameters being worked on in the experiment generator.
        """
        mean_latency = kwargs['latency_mean']

        if node['consistency'] == Consistency.STRONG:
            # Add raft-specific information
            node['election_timeout']   = [
                mean_latency * 10, mean_latency * 20
            ]
            node['heartbeat_interval'] = mean_latency * 5

        if node['consistency'] == Consistency.TAG:
            # Add tagging-specific information
            node['session_timeout'] = mean_latency * 20
            node['heartbeat_interval'] = mean_latency * 5

    def update_link_params(self, link, **kwargs):
        """
        In place update of the link in the JSON structure according to the
        parameters being worked on in the experiment generator.
        """
        if link['connection'] == VARIABLE:
            link['latency'] = kwargs['latency_range']

        elif link['connection'] == CONSTANT:
            link['latency'] = kwargs['latency_mean']

        elif link['connection'] == NORMAL:
            link['latency'] = [
                kwargs['latency_mean'], kwargs['latency_stddev']]

        else:
            link['latency'] = kwargs['latency_mean']

    def update_experiment_meta(self, experiment, **kwargs):
        """
        In place update of the experiment meta data witih keyword arguments.
        """
        for key, val in kwargs.items():
            experiment['meta'][key] = val

##########################################################################
## Vary anti-entropy delays
##########################################################################

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


##########################################################################
## Federated Experiment Generator
##########################################################################

class FederatedLatencyVariation(LatencyVariation):
    """
    A specialization of the latency variation mechanism that only varies the
    latency in the wide area (not the local area) and updates node parameters
    such as anti-entropy delay, heartbeat interval, and election timeout with
    a "tick" measure as computed by either the Bailis or the the Howard
    measurements. Note therefore that the parameters are entirely dependent on
    the latency of the WIDE area (not the local area).
    """

    def get_defaults(self, options):
        """
        Update the LatencyVariation defaults with anti-entropy options.
        """
        defaults = nested_update({
            'tick_metric': {
                'method': 'howard', # Can be either Howard or Bailis for now.
            }
        }, options)

        return super(FederatedLatencyVariation, self).get_defaults(defaults)

    def latencies(self, n):
        """
        Computes tick (T), and associates it with the latency arguments
        computed by the super class (LatencyVariation).

        T is a parameter that is measured from the mean and stddev of latency.

        The howard model proposes T = 2(mu + 2sd)
        The bailis model proposes T = 10mu
        """

        # Model mapping
        models = {
            'bailis': lambda mu, sd: 10*mu,
            'howard': lambda mu, sd: 2*(mu + (2*sd)),
        }

        # Select the model
        model = self.options['tick_metric']['method']
        if model not in models:
            raise BadValue(
                "Unknown model '{}', choose from {}".format(
                    model, ", ".join(models.keys())
                )
            )


        for latency in super(FederatedLatencyVariation, self).latencies(n):
            # Add the tick metrick to the latency parameters
            latency['tick_metric'] = int(round(models[model](
                latency['latency_mean'], latency['latency_stddev']
            )))
            yield latency

    def update_node_params(self, node, **kwargs):
        """
        Node parameters are set based on T

        Raft parameters are set as follows:

            - heartbeat interval = T/2
            - election timeout = (T, 2T)

        Eventual parameters are set as follows:

            - anti-entropy delay = T/4
        """
        tick = kwargs['tick_metric']

        if node['consistency'] == Consistency.STRONG:
            # Add raft-specific information
            node['election_timeout']   = [tick, 2*tick]
            node['heartbeat_interval'] = int(round(float(tick) / 2.0))

        if node['consistency'] == Consistency.EVENTUAL:
            # Add eventual-specific information
            node['anti_entropy_delay'] = int(round(float(tick) / 4.0))

    def update_link_params(self, link, **kwargs):
        """
        In place update of the link in the JSON structure according to the
        parameters being worked on in the experiment generator.
        """
        # Do not modify "local" area links if specified in the topology.
        if link.get('area', None) == LOCAL_AREA:
            return

        # Otherwise pass the link off to the super class to get modified. 
        return super(FederatedLatencyVariation, self).update_link_params(link, **kwargs)
