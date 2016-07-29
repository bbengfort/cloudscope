# cloudscope.simulation.workload.traces
# Methodology for loading accesses from a file and replaying them.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jul 27 12:45:04 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: traces.py [] benjamin@bengfort.com $

"""
Methodology for loading accesses from a file and replaying them.
"""

##########################################################################
## Imports
##########################################################################

from .base import Workload

from collections import namedtuple
from cloudscope.utils.decorators import memoized
from cloudscope.utils.timez import humanizedelta
from cloudscope.replica.access import READ, WRITE
from cloudscope.exceptions import WorkloadException


##########################################################################
## Module Constants
##########################################################################

# Data storage for parsing the TSV file.
TraceAccess = namedtuple("TraceAccess", "timestep, replica, object, method")


##########################################################################
## Traces Parser
##########################################################################

class TracesParser(object):
    """
    A generator that yields and parses accesses from a trace file.
    """

    def __init__(self, path):
        """
        Primary input is the location on disk of the traces.
        """
        self.path = path

    def parse(self, line):
        """
        Parses and validates a line from a traces file.
        """
        # Parse the line, splitting on whitespace
        line = line.strip().split()

        # If no object is specified, insert None
        if len(line) == 3:
            line.insert(2, None)

        # Validate the length
        if len(line) != 4:
            raise WorkloadException(
                "Unparsable line: '{}'".format(" ".join(line))
            )

        # Validate the access
        if line[3] not in {READ, WRITE}:
            raise WorkloadException(
                "Unknown access '{}' must be read or write".format(line[3])
            )

        # Parse the various fields
        line[0] = int(float(line[0]))
        line[3] = line[3].lower()

        return TraceAccess(*line)

    def __iter__(self):
        """
        Reads the traces and yields the access tuple. Assumes a file format:

            timestep    replica    object    method

        If the row is length three instead of length for a None is inserted
        for the object in the 2nd position.
        """
        with open(self.path, 'r') as fobj:
            for line in fobj:
                yield self.parse(line)


##########################################################################
## Traces Workload
##########################################################################

class TracesWorkload(Workload):
    """
    Deterministic method of providing a workload through traces - a TSV file
    that contains the timestamp, the replica ID, the object name and the
    access method (read/write).
    """

    def __init__(self, path, sim, **kwargs):
        self.path   = path                # path on disk to the access trace
        self.reader = TracesParser(path)  # handle to traces reader object
        self.clock  = 0                   # maintain the time since last access
        self.count  = 0                   # number of objects in the trace file

        # Create an empty list of objects to track what's being written.
        kwargs['objects'] = set(kwargs.get('objects', []))

        # Initialize the Process
        super(TracesWorkload, self).__init__(sim, **kwargs)

    @memoized
    def devices(self):
        """
        Mapping of replica IDs to device for easy selection.
        """
        return {
            device.id: device
            for device in self.sim.replicas
        }

    def update(self, trace=None, **kwargs):
        """
        Update the state of the workload based on data from the traces file.
        """
        self.count  += 1
        self.clock   = self.env.now
        self.current = trace
        self.device  = self.devices.get(trace.replica, None)
        self.objects.add(trace.object)

        # ensure that the device exists
        if self.device is None:
            raise WorkloadException(
                "Unknown device with replica id '{}'".format(trace.replica)
            )

        # Call to the super update method
        super(TracesWorkload, self).update(**kwargs)

    def wait(self):
        """
        Compute the delay until the next access based on data from the traces
        file; raise an exception if we've accidentally gone backward in time.
        """
        # validate that the access occurs now or at the clock
        if self.current.timestep < self.clock:
            raise WorkloadException(
                "Unordered access '{}' occurred at clock {}".format(
                    self.current, self.clock
                )
            )

        # wait until timestep for access occurs
        return self.current.timestep - self.clock

    def access(self):
        """
        Trigger the last access that has been read from the traces file.
        """
        # Save some typing
        trace = self.current

        # Log the results on the timeseries for the access.
        self.sim.results.update(
            trace.method, (self.device.id, self.location, trace.object, self.env.now)
        )

        # Perform the access on the device
        if trace.method == READ:
            return self.device.read(trace.object)

        if trace.method == WRITE:
            return self.device.write(trace.object)

    def run(self):
        """
        Reads in the accesses (which must be ordered by timestep) and updates
        the environment with delays and calls as required. Note this process
        is fundamentally different than the super class.
        """

        # Read through accesses in an ordered fashion.
        # Note this will only generate accesses until they are exhausted.
        for trace in self.reader:

            # Update the state of the workload with the new access
            self.update(trace)

            # Timeout according to the wait on the trace and update clock
            wait  = self.wait()
            yield self.env.timeout(wait)

            # Execute the access on the device
            access = self.access()
            assert access is not None

            # Log (debug) the access
            self.sim.logger.debug(
                "{} access by {} on {} (at {}) after {}".format(
                    access, self.name, self.device, self.device.location,
                    humanizedelta(milliseconds=wait)
                )
            )
