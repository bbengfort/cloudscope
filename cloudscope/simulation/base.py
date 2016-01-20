# cloudscope.simulation.base
# The API for simulation processes and scripts.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Jan 20 06:05:28 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: base.py [] benjamin@bengfort.com $

"""
The API for simulation processes and scripts.
"""

##########################################################################
## Imports
##########################################################################

import simpy
import random

from datetime import datetime
from cloudscope.config import settings
from cloudscope.dynamo import Sequence
from cloudscope.results import Results
from cloudscope.utils.decorators import memoized
from cloudscope.utils.timez import HUMAN_DATETIME
from cloudscope.utils.logger import SimulationLogger


##########################################################################
## Process Objects for Simulation
##########################################################################

class Process(object):
    """
    Base process object.
    """

    def __init__(self, env):
        self.env    = env
        self.action = env.process(self.run())

    def run(self):
        raise NotImplementedError("Processes must implement a run method.")


class NamedProcess(Process):
    """
    A process with a sequence counter and self identification.
    """

    counter = Sequence()

    def __init__(self, env):
        self._id = self.counter.next()
        super(NamedProcess, self).__init__(env)

    @property
    def name(self):
        return "{} #{}".format(self.__class__.__name__, self._id)


##########################################################################
## Base Simulation Script
##########################################################################

class Simulation(object):


    def __init__(self, **kwargs):
        """
        Instantiates the simpy environment and other configurations.
        """
        random.seed(kwargs.get('random_seed', settings.simulation.random_seed))

        self.max_sim_time = kwargs.get('max_sim_time', settings.simulation.max_sim_time)
        self.env = simpy.Environment()

    @memoized
    def name(self):
        """
        Override to set a specific name for the simulation.
        """
        return self.__class__.__name__

    @memoized
    def results(self):
        """
        Auto-configure the results object before being accessed.
        """
        return Results(simulation=self.name)

    @memoized
    def logger(self):
        """
        Insantiates and returns a SimulationLogger instance.
        """
        return SimulationLogger(self.env)

    def script(self):
        """
        Use the environment to generate a script.
        """
        raise NotImplementedError("Every simulation requires a script.")

    def setup(self):
        """
        Override to do any work before the simulation runs like logging or
        cleaning up output files. Call super to ensure logging works.
        """
        message = (
            "{} Simulation started at {}"
            .format(self.name, datetime.now().strftime(HUMAN_DATETIME))
        )

        self.logger.info(message)

    def complete(self):
        """
        Override for a final report or cleanup at the end of the run.
        Call super to ensure logging works correctly
        """
        message = (
            "{} Simulation finshed at {} ({})"
            .format(
                self.name,
                datetime.now().strftime(HUMAN_DATETIME),
                self.results.timer
            )
        )

        self.logger.info(message)

    def run(self):
        """
        The entry point for all simulations.
        """
        # Call setup and initialization function
        self.setup()

        # Time the entire simulation run process.
        with self.results.timer:

            # Set up the simulation environment and run
            self.script()
            self.env.run(until=self.max_sim_time)

        # Call clean and completion functions
        self.complete()
