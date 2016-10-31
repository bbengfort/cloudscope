# cloudscope.simulation.workload.base
# A refactoring of the original workload objects for multiple purposes.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Jan 26 08:43:19 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: base.py [1efa3ed] benjamin@bengfort.com $

"""
A refactoring of the original workload objects for multiple purposes.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.config import settings
from cloudscope.utils.decorators import memoized
from cloudscope.utils.timez import humanizedelta
from cloudscope.replica.access import READ, WRITE
from cloudscope.simulation.base import NamedProcess
from cloudscope.exceptions import WorkloadException
from cloudscope.dynamo import BoundedNormal, Bernoulli, Discrete


##########################################################################
## Base Workload Object
##########################################################################

class Workload(NamedProcess):
    """
    The base object from which all types of workloads are derived. The
    workload is a simulation process that will cause accesses (usually reads
    and writes) to occur, simulating user behavior in a distributed storage
    system. Subclasses of workloads may generate random user behavior or read
    a script from a file to execute the behavior.

    Workloads must be instantiated with the simulation environment, and then
    will use the simulation's environment to instantiate its own process.
    The simulation will also accept keyword arguments for various parameters.
    """

    def __init__(self, sim, device=None, objects=None, current=None, **extra):
        """
        Initialization requires a simulation, from which it derives many of
        the simulation environment like the SimPy environment and the topology
        of the network. The following optional arguments are:

            - device: the replica where the accesses occur
            - objects: the set of objects the replica can access
            - current: the object currently being accessed
            - extra: any extra keyword arguments are stored here

        If None is passed into these parameters, it is expected subclasses
        will handle them; primarily by using a property with a set function
        specified on the descriptor.
        """

        self.sim = sim          # The parent simulation
        self.device  = device   # The device where accesses occur
        self.objects = objects  # The set of possible objects to open
        self.current = current  # The currently open object being accessed
        self.extra   = extra    # Any extra keyword arguments

        # Initialize the Process
        super(Workload, self).__init__(sim.env)

    @memoized
    def name(self):
        """
        Overrides the workload to specify what user is working.
        """
        return "user {}".format(self._id)

    @property
    def location(self):
        """
        Shortcut to access the device location
        """
        if self.device is None: return None
        return self.device.location

    def update(self, **kwargs):
        """
        The update method is called after every triggered access while the
        simulation is running. Subclasses can choose to override this method
        to ensure that the workload is correctly adapted for that scenario.
        """
        pass

    def wait(self):
        """
        This method is called to determine how long to wait between accesses.
        Subclasses can override this method to simulate random periods.

        :returns: an integer specifying the delay until the next access.
        """
        raise NotImplementedError(
            "Subclasses must specify how long to wait between accesses!"
        )

    def access(self):
        """
        This method is called in order to trigger an access by the simulated
        user/workload and must return that access to the primary process for
        logging and tracing the information in the system.
        """
        raise NotImplementedError(
            "Subclasses must specify how to trigger accesses!"
        )

    def run(self):
        """
        The workload generating action that is correct for most subclasses,
        so long as they modify the update, wait, and access methods correctly.

        This method rountinely triggers accesses, updates the state of the
        workload, and logs the progress of the workload.
        """
        while True:
            # Wait for the next access interval
            wait = self.wait()
            yield self.env.timeout(wait)

            # Trigger the access
            access = self.access()
            assert access is not None

            # Log (debug) the access
            self.sim.logger.debug(
                "{} access by {} on {} (at {}) after {}".format(
                    access, self.name, self.device, self.location,
                    humanizedelta(milliseconds=wait)
                )
            )

            # Update the state of the workload
            self.update()


##########################################################################
## Routine Workload
##########################################################################

class RoutineWorkload(Workload):
    """
    A routine workload generates accesses according to the following params:

        - A normal distribution time between accesses
        - A probability of reads (vs. writes)
        - A probability of switching objects (vs. continuing with current)

    This is the simplest workload that is completely implemented.
    """

    def __init__(self, sim, **kwargs):
        """
        Initialize workload probabilities and distributions before passing
        all optional keyword arguments to the super class.
        """

        # Distribution for whether or not to change objects
        self.do_object = Bernoulli(kwargs.pop('object_prob', settings.simulation.object_prob))
        self.do_read = Bernoulli(kwargs.pop('read_prob', settings.simulation.read_prob))

        # Interval distribution for the wait (in ms) to the next access.
        self.next_access = BoundedNormal(
            kwargs.pop('access_mean', settings.simulation.access_mean),
            kwargs.pop('access_stddev', settings.simulation.access_stddev),
            floor = 1.0,
        )

        # Initialize the Workload
        super(RoutineWorkload, self).__init__(sim, **kwargs)

        # If current is None, update the state of the workload:
        if self.current is None: self.update()

    def update(self, **kwargs):
        """
        Uses the do_object distribution to determine whether or not to change
        the currently accessed object to a new object.
        """

        # Do we switch the current object?
        if self.current is None or self.do_object.get():

            if len(self.objects) == 1:
                # There is only one choice, no switching!
                self.current = self.objects[0]

            else:
                # Randomly select an object that is not the current object.
                self.current = Discrete([
                    obj for obj in self.objects
                    if obj != self.current
                ]).get()

        # Call to the super update method
        super(RoutineWorkload, self).update(**kwargs)

    def wait(self):
        """
        Utilizes the bounded normal distribution to return the wait (in
        milliseconds) until the next access.
        """
        return self.next_access.get()

    def access(self):
        """
        Utilizes the do_read distribution to determine whether or not to
        issue a write or a read access, and calls the device method for it.
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

        # Determine if we are reading or writing.
        access = READ if self.do_read.get() else WRITE

        # Log the results on the timeseries for the access.
        self.sim.results.update(
            access, (self.device.id, self.location, self.current, self.env.now)
        )

        if access == READ:
            # Read the latest version of the current object
            return self.device.read(self.current)

        if access == WRITE:
            # Write to the current version (e.g. call nextv)
            return self.device.write(self.current)
