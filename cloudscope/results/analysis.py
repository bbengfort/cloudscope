# cloudscope.results.analysis
# Analysis utilities for dealing with cloudscope results.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Jun 23 19:17:14 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: analysis.py [a6562cb] benjamin@bengfort.com $

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
        mtypes = Counter()
        for val in values:
            mtypes[val[3]] += 1

        return {
            label: len(values),
            "message types": dict(mtypes),
        }

    def handle_recv(self, label, values):
        """
        Expects a time series in the form of:

            (target, source, recv at, message type, delay)

        Returns the number of received messages and the average dleay
        """
        return {
            label: len(values),
            "mean message latency (ms)": mean(v[4] for v in values),
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

    def handle_missed_reads(self, label, values):
        """
        Expects a time series in the form of:

            (owner, timestamp)

        Returns the number of missed reads
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

    def handle_missed_read_latency(self, label, values):
        """
        Expects a time series in the form of:

            (owner, version, started, finished)

        Returns the mean read missed latency
        """
        return {
            "mean missed read latency (ms)": mean(v[3] - v[2] for v in values),
        }

    def handle_stale_reads(self, label, values):
        """
        Expects a time series in the form of:

            (owner, timestamp, created, latest version, read version)

        Returns the number of stale reads, mean time, and version staleness.
        """
        time_stale = [v[1] - v[2] for v in values]
        vers_stale = [v[3] - v[4] for v in values]

        return {
            label: len(values),
            "cumulative read time staleness (ms)": sum(time_stale),
            "mean read time staleness (ms)": mean(time_stale),
            "mean read version staleness": mean(vers_stale),
        }

    def handle_stale_writes(self, label, values):
        """
        Expects a time series in the form of:

            (owner, timestamp, created, latest version, read version)

        Returns the number of stale writes, mean time, and version staleness.
        """
        time_stale = [v[1] - v[2] for v in values]
        vers_stale = [v[3] - v[4] for v in values]

        return {
            label: len(values),
            "cumulative write time staleness (ms)": sum(time_stale),
            "mean write time staleness (ms)": mean(time_stale),
            "mean write version staleness": mean(vers_stale),
        }

    def handle_dropped_writes(self, label, values):
        """
        Expects a time series in the form of:

            (owner, timestamp)

        Returns the number of dropped_writes
        """
        return {
            label: len(values),
        }

    def handle_visibility(self, label, values):
        """
        Expects a time series in the form of:

            (writer, version, percent visible, created, updated)

        Returns the average visibility of all the writes as well as the
        number of partially visible writes.
        """
        accesses = defaultdict(float)
        delays   = defaultdict(int)
        for val in values:
            if val[2] > accesses[val[1]]:
                accesses[val[1]] = val[2]

            if val[4] > delays[(val[1], val[3])]:
                delays[(val[1], val[3])] = val[4]

        return {
            'mean visibility': mean(accesses.values()),
            'partially visible writes': sum(1 for pcent in accesses.values() if pcent < 1.0),
            'mean partial visibility latency (ms)': mean(
                val - key[1] for key, val in delays.items()
            )
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

    def handle_dropped_write_latency(self, label, values):
        """
        Expects a time series in the form of:

            (owner, version, started, finished)

        Returns the mean dropped write latency
        """
        return {
            "mean dropped write latency (ms)": mean(v[3] - v[2] for v in values),
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
        for node in topology['nodes']:
            if node['id'] == replica:
                row.update(node)
                break

        # Help with missing keys

        # Append the row to the table
        table.append(row)

    # Create the data frame and compute final aggregations
    df = pd.DataFrame(sorted(table, key=itemgetter('replica')))
    df['partially replicated writes'] = df['writes'] - df ['visible writes']
    df['visibility ratio'] = df['visible writes'] / df['writes']

    # Remove the "unforked writes"
    if 'unforked writes' in df.columns:
        df['forked writes'] -= df['unforked writes']

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

def result_value(result, *keys):
    """
    Collects a key from the result object or dictionary, supporting nested
    keys and complex object lookups. See also iter_results_values.
    """
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, {})
        else:
            result = getattr(result, key, {})

    return result


def iter_results_values(results, *keys):
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
        yield result_value(result *keys)


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
    for idx, result in enumerate(results):
        data = {'eid': "e{:0>2}".format(idx)}
        conf = result_value(result, 'settings')

        # Pull information from the configuration
        data['type'] = conf['type']
        data['users'] = conf['users']
        data['tick metric (T)'] = conf['tick_metric']
        data['mean latency (ms)'] = conf['latency_mean']
        data['latency range (ms)'] = conf['latency_range']
        data['standard deviation of latency (ms)'] = conf['latency_stddev']
        data['anti-entropy delay (ms)'] = conf['anti_entropy_delay']
        data['heartbeat interval (ms)'] = conf['heartbeat_interval']
        data['election timeout (ms, ms)'] = conf['election_timeout']
        data['T parameter model'] = conf['tick_param_model']
        data['conflict probability'] = conf['conflict_prob']
        data['outage probability'] = conf['outage_prob']
        data['sync probability'] = conf['sync_prob']
        data['local probability'] = conf['local_prob']

        # Aggregate the timeseries resuts data
        for key, values in result_value(result, 'results').iteritems():
            data.update(aggregator(key, values))

        # If we didn't do an aggregation from the time series, get it
        # directly from the messages and latencies objects.
        messages  = result.messages.messages
        latencies = result.latencies

        if 'message types' not in data:
            data['message types'] = messages.get('sent', {})

        if 'sent' not in data:
            data['sent messages'] = sum(messages.get('sent', {}).values())

        if 'recv' not in data:
            data['recv messages'] = sum(messages.get('recv', {}).values())

        if 'dropped' not in data:
            data['dropped messages'] = sum(messages.get('drop', {}).values())

        # Get the simulation time from the results
        data['simulation time (secs)'] = result.timer['finished'] - result.timer['started']

        table.append(data)

    df = pd.DataFrame(table)
    df = df.fillna(0)

    # Remove the "unforked writes"
    if 'unforked writes' in df.columns:
        df['inconsistent writes'] = df['forked writes'] - df['unforked writes']

    return df
