# cloudscope.results.analysis
# Analysis utilities for dealing with cloudscope results.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Jun 23 19:17:14 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: analysis.py [] benjamin@bengfort.com $

"""
Analysis utilities for dealing with cloudscope results.
"""

##########################################################################
## Imports
##########################################################################

from operator import itemgetter
from collections import defaultdict, Counter

from cloudscope.utils.statistics import mean, median
from cloudscope.utils.strings import snake_case
from cloudscope.exceptions import BadValue
from peak.util.imports import lazyModule

# Perform lazy loading of vizualiation libraries
pd  = lazyModule('pandas')

##########################################################################
## Time Series Handlers
##########################################################################

class TimeSeriesAggregator(object):
    """
    This complex class can handle the results time series data by key. A
    single instance is a callable that takes a key and an iterable of values,
    it then routes the value to the appropriate handler based on the key and
    returns a dictionary of the aggregates computed by key.

    If no handler is associated with the key, then by default it just counts
    the number of items in the time series (len). No exceptions are raised.
    """

    def __call__(self, key, values, label=None):
        """
        The entry point for handling all time series aggregation. This method
        decides on the aggreagator to use, or by default just counts the
        instances in the series (values). Returns a dictionary of aggregates.

        You can also rename the key with a label for better visibility in
        analytics & visualizations. If label is None, key is used. Note that
        many handlers will simply ignore the label, however.
        """
        # Compute the method name
        handler = "handle_{}".format(snake_case(key))

        # Check if the method exists on the class
        # If not, use the default handler specified by the class
        if hasattr(self, handler):
            handler = getattr(self, handler)
        else:
            handler = self.default_handler

        # Return the results of the aggregate by the handler.
        label = label or key
        return handler(label, values)

    def default_handler(self, label, values):
        """
        The default handler simply counts the number of items in the series.
        """
        return {
            label: len(values),
        }

    def handle_sent(self, label, values):
        """
        Expects a time series in the form of:

            (source, target, sent at, message type)

        Returns the total number of sent messages
        """
        return {
            label: len(values),
        }

    def handle_recv(self, label, values):
        """
        Expects a time series in the form of:

            (target, source, recv at, message type, delay)

        Returns the number of sent messages and the average dleay
        """
        mtypes = Counter()
        for val in values:
            mtypes[val[3]] += 1

        return {
            label: len(values),
            "mean message latency (ms)": mean(v[4] for v in values),
            "message types": dict(mtypes),
        }

    def handle_read(self, label, values):
        """
        Expects a time series in the form of:

            (replica, location, object, timestamp)

        Returns the total number of reads
        """
        return {
            "reads": len(values),
        }

    def handle_write(self, label, values):
        """
        Expects a time series in the form of:

            (replica, location, object, timestamp)

        Returns the total number of writes
        """
        return {
            "writes": len(values),
        }

    def handle_empty_reads(self, label, values):
        """
        Expects a time series in the form of:

            (owner, timestamp)

        Returns the number of empty reads
        """
        return {
            label: len(values),
        }

    def handle_read_latency(self, label, values):
        """
        Expects a time series in the form of:

            (owner, version, started, finished)

        Returns the mean read latency and the number of completed reads
        """
        return {
            "completed reads": len(values),
            "mean read latency (ms)": mean(v[3] - v[2] for v in values),
        }

    def handle_stale_reads(self, label, values):
        """
        Expects a time series in the form of:

            (owner, timestamp)

        Returns the number of stale reads
        """
        return {
            label: len(values),
        }

    def handle_visibility_latency(self, label, values):
        """
        Expects a time series in the form of:

            (replica, version, created, updated)

        Returns the mean time delta and the number of visible writes
        """
        return {
            "mean visibility latency (ms)": mean(v[3] - v[2] for v in values),
            "visible writes": len(set([v[1] for v in values])),
        }

    def handle_commit_latency(self, label, values):
        """
        Expects a time series in the form of:

            (replica, version, created, updated)

        Returns the mean time delta and the number of committed writes
        """
        return {
            "mean commit latency (ms)": mean(v[3] - v[2] for v in values),
            "committed writes": len(set([v[1] for v in values])),
        }

    def handle_write_latency(self, label, values):
        """
        Expects a time series in the form of:

            (replica, version, started, finished)

        Returns the mean write latency and the number of completed writes
        """
        return {
            "completed writes": len(values),
            "mean write latency (ms)": mean(v[3] - v[2] for v in values),
        }

    def handle_session_length(self, label, values):
        """
        Expects a time series in the form of:

            (replica, duration)

        Returns the mean duration and the number of sessions
        """
        return {
            "sessions": len(values),
            "mean session duration (ms)": mean(v[1] for v in values),
        }

    def handle_tag_size(self, label, values):
        """
        Expects a time series in the form of:

            (replica, timestamp, tag size)

        Returns the mean tag size
        """
        return {
            "average tag size": mean(v[2] for v in values),
        }


## Hook to a single instance of the aggregator
aggregator = TimeSeriesAggregator()


##########################################################################
## DataFrame creation utilities
##########################################################################

def create_per_replica_dataframe(results):
    """
    Expects a single results object and creates a data frame, aggregating
    values on a per-replica basis rather than on a per experiment basis.
    """

    if isinstance(results, (list, tuple)):
        raise BadValue(
            "This analysis function works only on a single results object"
        )

    # Set up the various data structures we will be using
    replicas = defaultdict(lambda: defaultdict(list))
    topology = results.topology
    config   = results.settings
    series   = results.results

    # Separate the series into per-replica series
    for key, values in series.iteritems():
        for value in values:
            # Append the item from the series to the correct replica series
            replicas[value[0]][key].append(value)

    # Create a table with each replica id
    table = []
    for replica, series in replicas.iteritems():
        row = {'replica': replica}

        # Perform per-replica aggregations for each series
        for key, values in series.iteritems():
            row.update(aggregator(key, values))

        # Add in topology information

        # Help with missing keys

        # Append the row to the table
        table.append(row)

    # Create the data frame and compute final aggregations
    df = pd.DataFrame(sorted(table, key=itemgetter('replica')))
    df['missed reads'] = df['reads'] - df['completed reads']
    df['dropped writes'] = df['writes'] - df ['visible writes']
    df['visibility ratio'] = df['visible writes'] / df['writes']

    return df


def create_messages_dataframe(results):
    """
    Creates a DataFrame of messages in order to analyze communications.
    """

    if isinstance(results, (list, tuple)):
        raise BadValue(
            "This analysis function works only on a single results object"
        )

    # Specify the modes we want to count messages on
    # Specify the fields name in the sent/recv timeseries
    modes  = ('sent', 'recv')
    fields = ['replica', 'timestamp', 'type', 'latency']

    def messages(results):
        """
        Inner generator for looping through the sent and recv series.
        """
        for mode in modes:
            for value in results[mode]:
                msg = dict(zip(fields, value))
                msg['recv'] = 1 if mode == 'recv' else 0
                msg['sent'] = 1 if mode == 'sent' else 0
                yield msg

    return pd.DataFrame(messages(results.results))


##########################################################################
## Results collection utilities
##########################################################################

def results_values(results, *keys):
    """
    Collects all the values for a particular key or nested keys from all
    results in the results collection. Input can be either a Results object
    or a dictionary loaded from a JSON file.
    """

    try:
        results = iter(results)
    except TypeError:
        raise BadValue(
            "This analysis function requires a collection of results objects"
        )

    for result in results:
        # Each result is a single Result object or a dict
        # Continue fetching value from each subkey
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key, {})
            else:
                result = getattr(result, key, {})

        # Yield the value for this result
        yield result


def create_settings_dataframe(results, exclude=None):
    """
    Creates a per-experiment DataFrame of different settings for each.
    Can specify a list of settings to exclude from the data frame.
    """
    table = defaultdict(dict)

    # Add the seettings from the results object
    for idx, conf in enumerate(results_values(results, 'settings')):
        # Identify the experiment by index
        eid = "e{:0>2}".format(idx)
        table[eid]['name'] = eid

        # Add all attributes from the settings dict
        for key, val in conf.iteritems():
            if exclude is not None and key in exclude: continue
            table[eid][key] = val

    # Override or add additional settings from the topology meta
    for idx, conf in enumerate(rvals('topology', 'meta')):
        # Identify the experiment by index
        eid = "e{:0>2}".format(idx)

        # Add all attributes from the meta dict
        for key, val in conf.iteritems():
            if exclude is not None and key in exclude: continue
            table[eid][key] = val

    return pd.DataFrame(table.values())


def create_per_experiment_dataframe(results):
    """
    Creates a DataFrame of aggregations per experiment rather than per replica
    by iterating through a list of results objects. This does not really work
    for a single results object, and so this function expects a list or tuple.
    """

    try:
        iter(results)
    except TypeError:
        raise BadValue(
            "This analysis function requires a collection of results objects"
        )

    table = []
    conf  = list(results_values(results, 'settings'))

    for idx, results in enumerate(results_values(results, 'results')):
        data = {'eid': "e{:0>2}".format(idx)}

        # Pull information from the configuration
        data['type'] = conf[idx]['type']
        data['users'] = conf[idx]['users']
        data['tick metric (T)'] = conf[idx]['tick_metric']
        data['mean latency (ms)'] = conf[idx]['latency_mean']
        data['latency range (ms)'] = conf[idx]['latency_range']
        data['standard deviation of latency (ms)'] = conf[idx]['latency_stddev']
        data['anti-entropy delay (ms)'] = conf[idx]['anti_entropy_delay']
        data['heartbeat interval (ms)'] = conf[idx]['heartbeat_interval']
        data['election timeout (ms, ms)'] = conf[idx]['election_timeout']

        # TODO: Replace with actual data
        # data['T parameter model'] = conf[idx]['tick_param_model']
        data['T parameter model'] = 'bailis'

        # Aggregate the timeseries resuts data
        for key, values in results.iteritems():
            data.update(aggregator(key, values))

        table.append(data)

    return pd.DataFrame(table)
