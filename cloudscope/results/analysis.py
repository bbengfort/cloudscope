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

from cloudscope.utils.statistics import mean, median

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
        handler = "handle_{}".format(key.replace(" ", "_").lower())

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

            (replica, sent at, message type)

        Returns the total number of sent messages
        """
        return {
            label: len(values),
        }

    def handle_recv(self, label, values):
        """
        Expects a time series in the form of:

            (replica, recv at, message type, delay)

        Returns the number of sent messages and the average dleay
        """
        return {
            label: len(values),
            "mean message latency (ms)": mean(v[3] for v in values),
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
