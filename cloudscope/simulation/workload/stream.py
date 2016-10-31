# cloudscope.simulation.workload.stream
# Workloads that continuously stream the next access.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Oct 31 10:08:34 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: stream.py [f833e25] benjamin@bengfort.com $

"""
Workloads that continuously stream the next access.
"""

##########################################################################
## Imports
##########################################################################

from .base import Workload
from cloudscope.replica.access import Read, Write, READ, WRITE
from cloudscope.replica.access import COMPLETED, DROPPED, UPDATED


##########################################################################
## Streaming workload
##########################################################################

class StreamingWorkload(Workload):
    """
    A streaming workload issues accesses one after the other as soon as the
    previous access is dropped or completed (with some minimal delay between
    accesses that can be specified by overriding the `wait` method).
    """

    def __init__(self, sim, **kwargs):

        # Get the delay in milliseconds if specified
        self.delay  = kwargs.pop("delay", 10)

        # Internal parameters
        self._event  = None
        self._access = None

        # Initialize the workload
        super(StreamingWorkload, self).__init__(sim, **kwargs)

    def on_access_drop(self, access):
        # Retry the access after a delay
        self._access = access.clone(self.device)
        self._event.succeed()

    def on_access_complete(self, access):
        # Set the access to None to generate a new write
        self._access = None
        self._event.succeed()

    def on_event_complete(self, event):
        # Wait for a bit and execute the next access!
        self.env.process(self.wait())

    def wait(self):
        """
        Wait a fixed delay and then cause the access to occur!
        """
        yield self.env.timeout(self.delay)
        yield self.access()

    def access(self):
        """
        Sets up a SimPy event to wait for the access to complete or drop.
        Note that accesses are only writes - as though this were a sensor just
        streaming write accesses to the file system!
        """
        # Make sure that there is a device to write to!
        if not self.device:
            raise WorkloadException(
                "No device specified to trigger the access on!"
            )

        # Make sure that there is a current object to write!
        if not self.current:
            raise WorkloadException(
                "No object specified as currently open on the workload!"
            )

        # Log the results on the timeseries for the access.
        self.sim.results.update(
            WRITE, (self.device.id, self.location, self.current, self.env.now)
        )

        # Create the event to wait for the access to complete
        self._event  = self.env.event()
        self._event.callbacks.append(self.on_event_complete)

        # Create the access and register the event callbacks
        if self._access is None:
            self._access = Write(self.current, self.device)
            self._access.register_callback(COMPLETED, self.on_access_complete)
            self._access.register_callback(DROPPED, self.on_access_drop)

        # Write the access to the local device
        self.device.write(self._access)

        # Return the event to register it with the simulation process
        return self._event

    def run(self):
        """
        Sets off the first event that starts streaming access events.
        """
        return self.wait()
