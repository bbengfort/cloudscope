# -*- coding: utf-8 -*-
# cloudscope.results.consistency
# Support for consistency verification and checking after a simulation.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Sep 22 11:31:47 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: consistency.py [] benjamin@bengfort.com $

"""
Support for consistency verification and checking after a simulation.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.utils.statistics import mean
from cloudscope.utils.decorators import memoized, Timer

from tabulate import tabulate
from operator import itemgetter
from distance import nlevenshtein, jaccard
from collections import Counter, defaultdict


##########################################################################
## Primary consistency report object.
##########################################################################

class ConsistencyValidator(object):
    """
    Computes a consistency report from a simulation by analyzing what is in
    the logs of the replicas (and only the logs, with no other information).
    """

    @classmethod
    def deserialize(klass, data):
        """
        Consistency validators must be deserializable!
        """
        raise NotImplementedError(
            "Haven't quite figured out the API for this yet!"
        )

    def __init__(self):
        """
        Set the state of the validation.
        """
        self.validated  = False      # state of the validator
        self.n_objects  = None       # number of observed objects in logs
        self.n_entries  = None       # the number of unique entries in all logs
        self.namespace  = None       # the set of unique object names in logs
        self.logs       = None       # per-log replica analysis
        self.duplicates = None       # total number of duplicates
        self.mono_errs  = None       # total number of monotonically increasing errors
        self.forks      = None       # total number of forks in the log
        self.missing    = None       # total number of missing entries in all logs
        self.distance   = None       # pairwise distances between all the logs

    @memoized
    def name_classes(self):
        """
        Returns the set of all version classes (e.g. object names) in the
        system, particularly in order to compute the latest versions.
        """
        return frozenset(
            vers.__class__
            for log in self.logs.values()
            for vers in log.iter_versions()
        )


    def validate(self, simulation):
        """
        Entry point to consistency validation for a single simulation.
        """
        # Alert the user that validation is happening
        simulation.logger.info(
            "Beginning consistency validation ... may take some time."
        )

        with Timer() as t:

            # Mark the state as unvalidated in case of exceptions.
            self.validated = False

            # Extract the logs from the replicas for analysis.
            self.logs = {
                replica.id: LogMetric(replica.log)
                for replica in simulation.replicas
            }

            # Global metrics
            self.namespace = Counter()
            for log in self.logs.values(): self.namespace += log.namespace
            self.n_objects = len(self.namespace)
            self.n_entries = sum(name.counter.value for name in self.name_classes)

            # Count single log errors
            self.forks = sum(log.num_forks() for log in self.logs.values())
            self.duplicates = sum(log.num_duplicates() for log in self.logs.values())
            self.mono_errs = sum(log.num_monoincr_errors() for log in self.logs.values())
            self.missing = sum(log.num_missing() for log in self.logs.values())

            # Compute log similarities
            self.distance = defaultdict(lambda: defaultdict(dict))
            for ri, ri_log in self.logs.items():
                for rj, rj_log in self.logs.items():
                    self.distance['jaccard'][ri][rj] = ri_log.jaccard(rj_log)
                    self.distance['levenshtein'][ri][rj] = ri_log.levenshtein(rj_log)

            # Mark the state as validated
            self.validated = True

        # Alert the user that validation is complete
        simulation.logger.info(
            "Consistency validation complete, took {}.".format(t)
        )

    def log_inconsistency_table(self):
        """
        Returns a pretty table of log inconsistencies.
        """
        # The names of the fields in each row.
        keys = ["name", "entries", "forks", "monoincr errors", "duplicates", "missing"]

        # Append the per log entries
        table = [(
            name, log.n_entries, log.num_forks(), log.num_monoincr_errors(),
            log.num_duplicates(), log.num_missing(),
        ) for name, log in sorted(self.logs.items(), key=itemgetter(0))]

        # Append the totals from the log.
        table.append((
            'total', self.n_entries, self.forks, self.mono_errs, self.duplicates, self.missing
        ))

        return tabulate(table, headers=keys, tablefmt='simple')

    def split_log_distance_table(self):
        """
        Returns a matrix of levenshtein and jaccard distances.
        """

        keys  = [u'J↓ L→'] + sorted(self.logs.keys())
        table = []

        for idx, ri in enumerate(keys):
            if idx == 0: continue

            row = []
            distance = 'jaccard'

            for jdx, rj in enumerate(keys):
                # This is the name column in this case.
                if jdx == 0:
                    row.append(ri)
                    continue

                # We've reached the middle of the row.
                if ri == rj:
                    distance = 'levenshtein'

                row.append("{:0.2f}".format(self.distance[distance][ri][rj]))

            table.append(row)

        return tabulate(table, headers=keys, tablefmt='simple')

    def serialize(self):
        """
        ConsistencyValidator objects must have a serialize method to write to disk.
        """
        if not self.validated: return None

        def properties(self):
            for key, val in self.__dict__.iteritems():
                if not key.startswith('_') and not callable(val):
                    yield (key, val)

        return dict(properties(self))


##########################################################################
## Log Analysis
##########################################################################

class LogMetric(object):
    """
    Wraps a log and makes individual computations about it.
    """

    def __init__(self, log):
        # Log is a tuple of LogEntries (immutable)
        self.log = log.freeze()

        # Collect some simple information about the log
        self.namespace = Counter(version.name for version in self.iter_versions())
        self.n_entries = sum(self.namespace.values())

    def num_forks(self):
        """
        Counts the number of forked versions in the log.
        """
        return sum(
            1 if version.is_forked() else 0
            for version in self.iter_versions()
        )

    def num_monoincr_errors(self):
        """
        Returns the number of log entry pairs (for the same namespace) that
        do not have monotonically increasing version numbers.
        """
        prev  = defaultdict(int)
        fails = 0

        for version in self.iter_versions():
            if version.version < prev[version.name]: fails += 1
            prev[version.name] = version.version

        return fails

    def num_duplicates(self):
        """
        Returns the number of duplicate versions appended to the log.
        """
        # Create the set of all versions in the log.
        # Duplicates is the number of entries less the length of the set.
        uniques = set(str(version) for version in self.iter_versions())

        return self.n_entries - len(uniques)

    def num_missing(self):
        """
        For each name in the namespace, computes the number of present
        versions, relative to the highest version number accepted. There are
        a couple of caveats with this method:

            - Missing versions for any object not in the log aren't counted.
            - If there are "skips" in the version numbering, they will be misses
            - This may not work with Lamport scaler version numbers.

        This is a lightweight implementation for now.
        """
        missing = {
            name.__name__: name.counter.value
            for name in set(
                version.__class__ for version in self.iter_versions()
            )
        }

        for version in set(self.iter_versions()):
            missing[version.name] -= 1

        return sum(missing.values())

    def jaccard(self, other):
        """
        Computes the jaccard similarity between this log and the other one.
        """
        a = [str(version) for version in self.iter_versions()]
        b = [str(version) for version in other.iter_versions()]

        return jaccard(a,b)

    def levenshtein(self, other):
        """
        Computes the edit distance between this log and the other one and does
        not do it on name sequences, but rather on the entire log.
        """
        a = [str(version) for version in self.iter_versions()]
        b = [str(version) for version in other.iter_versions()]

        return nlevenshtein(a,b)

    def serialize(self):
        data = {
            "namespace": self.namespace,
            "num_entries": self.n_entries,
            "num_forks": self.num_forks(),
            "num_monoincr_errors": self.num_monoincr_errors(),
            "num_duplicates": self.num_duplicates(),
            "num_missing": self.num_missing(),
        }

        # Output the full log trace if requested
        if settings.simulation.trace_logs:
            data["log"] = [
                str(version) for version in self.iter_versions()
            ]

        return data

    def __iter__(self):
        # Iterate over all log entries in the log
        # Filtering out any "None" entries that are stubs
        for entry in self.log:
            if entry.version: yield entry

    def iter_versions(self):
        """
        Iterate through all the versions.
        """
        for entry in self: yield entry.version

    def iter_terms(self):
        """
        Iterate through all the terms in the log entries.
        """
        for entry in self: yield entry.term
