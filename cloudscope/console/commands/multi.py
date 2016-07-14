# console.commands.multi
# Multiprocess runner for running many simulations simultaneously.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Feb 17 19:13:06 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: multi.py [3b32635] benjamin@bengfort.com $

"""
Multiprocess runner for running many simulations simultaneously.
"""

##########################################################################
## Imports
##########################################################################

import os
import re
import json
import glob
import time
import logging
import argparse
import multiprocessing as mp

from commis import Command
from cStringIO import StringIO
from cloudscope.config import settings
from cloudscope.utils.decorators import Timer
from cloudscope.utils.timez import humanizedelta
from cloudscope.utils.notify import notify as send_mail
from cloudscope.simulation.main import ConsistencySimulation
from cloudscope.exceptions import NotifyError
from commis.exceptions import ConsoleError
from collections import Counter, defaultdict

## Special hack for now
TRACERE = re.compile(r'^trace-(\d+)ms-(\d+)user.tsv$')

##########################################################################
## Per process runner function
##########################################################################

def runner(idx, path, **kwargs):
    """
    Takes an open file-like object and runs the simulation, returning a
    string containing the dumped JSON results, which can be dumped to disk.
    """
    logger = logging.getLogger('cloudscope')

    try:

        with open(path, 'r') as fobj:
            sim = ConsistencySimulation.load(fobj, **kwargs)

        logger.info(
            "Starting simulation {}: \"{}\"".format(idx, sim.name)
        )
        sim.run()

        # Dump the output data to a file.
        output = StringIO()
        sim.results.dump(output)

        # Report completion back to the command line
        logger.info(
            "Simulation {}: \"{}\" completed in {}".format(idx, sim.name, sim.results.timer)
        )

        # Return the string value of the JSON results.
        return output.getvalue()

    except Exception as e:
        logger.error(
            "Simulation {} ({}) errored: {}".format(idx, path, str(e))
        )

        import traceback, sys
        return json.dumps({
            'idx': idx,
            'success': False,
            'traceback': "".join(traceback.format_exception(*sys.exc_info())),
            'error': str(e),
        })


##########################################################################
## Command
##########################################################################

class MultipleSimulationsCommand(Command):

    name = 'multisim'
    help = 'run multiple simulations with a varying network.'
    args = {
        ('-o', '--output'): {
            'type': argparse.FileType('w'),
            'default': None,
            'metavar': 'DST',
            'help': 'specify location to write output to',
        },
        ('-t', '--tasks'): {
            'type': int,
            'metavar': 'NUM',
            'default': mp.cpu_count(),
            'help': 'number of concurrent simulation task to run',
        },
        ('-T', '--trace'): {
            'type': str,
            'default': None,
            'metavar': 'PATH',
            'help': 'specify the path to the trace file with accesses',
        },
        ('-E', '--notify'): {
            'type': str,
            'default': None,
            'metavar': 'EMAIL',
            'help': 'specify an email address for notification when complete'
        },
        # Note: can't use argparse.FileType('r') here because of too many open files error!
        'topology': {
            'nargs': "+",
            'type': str,
            'default': None,
            'metavar': 'topology.json',
            'help': 'simulation description file to load'
        }
    }

    def handle(self, args):
        """
        Handles the multiprocess execution of the simulations.
        """
        # Disable Logging During Multiprocess
        logger = logging.getLogger('cloudscope.simulation')
        logger.disabled = True

        # Load the experiments and their options
        experiments = self.get_experiments(args)

        # Open an output file for results if one isn't specified
        if args.output is None:
            path = "multisim-results-{}.json".format("%Y%m%d%H%M%S", time.localtime())
            args.output = open(path, 'w+')

        # Create a pool of processes and begin to execute experiments
        with Timer() as timer:
            pool   = mp.Pool(processes=args.tasks)
            tasks  = [
                pool.apply_async(runner, (i+1,x), k)
                for i, (x, k) in enumerate(experiments)
            ]

            # Data structures for holding results
            deltas = []
            errors = []

            # Compute timing and errors and write results to disk
            # This causes the multisim to join!
            for task in tasks:

                # Pop the results off of the task queue
                result = json.loads(task.get())

                # If there is an error, add it to the errors and go on
                if 'error' in result:
                    errors.append(result)
                    continue

                # Otherwise append the timing duration
                deltas.append(
                    result['timer']['finished'] - result['timer']['started']
                )

                # And write the results to disk, one result per-line.
                # NOTE: This is the new style multi-result output for memory saving
                args.output.write(json.dumps(result) + "\n")

            # Compute duration
            duration = sum(deltas)

        # TIMER COMPLETE!
        # If traceback, dump the errors out.
        if args.traceback:
            for idx, error in enumerate(errors):
                banner = "="*36
                print ("{}\nError #{}:\n{}\n\n{}\n").format(
                    banner, idx+1, banner, error['traceback']
                )

        # Construct complete message for notification
        notice = (
            "{} simulations ({} compute time, {} errors) run by {} tasks in {}\n"
            "Results written to {}"
        ).format(
            len(tasks), humanizedelta(seconds=duration) or "0 seconds",
            len(errors), args.tasks, timer, args.output.name
        )

        self.notify(args.notify, notice, errors)
        return notice

    def get_experiments(self, args):
        """
        Returns experiment, keyword argument pairs for each experiment.
        """

        # Add partitions and other workload information
        # Or simply add those things to the topology to be run.
        options = {
            'trace': args.trace
        }

        for topology in args.topology:
            path = os.path.abspath(topology)

            if not os.path.exists(path) or not os.path.isfile(path):
                raise ConsoleError(
                    "Could not find topology file at '{}'".format(topology)
                )

            yield path, options

    def notify(self, recipient, notice, errors):
        """
        Notifies the recipient that the simulation is complete and sends the
        results and any errors as attachments.
        """

        # If no recipient is specified, don't worry about it
        if not recipient: return

        # Otherwise compose an actual message.
        message = (
            "Hello,\n\n"
            "This is the CloudScope multi-simulation command. "
            "I wanted to let you know the following:\n\n{}\n\n"
        ).format(notice)

        # Add the errors
        if errors:
            message += "The following errors occurred:\n\n"
            for error in errors:
                message += "    - {}\n".format(error['error'])
            message += "\n"
        else:
            message += "No errors occurred!\n\n"

        # Send the conclusion
        message += (
            "Thank you for simulating with CloudScope,\n"
            "The CloudScope Agent"
        )

        # Create the subject and the logger
        subject = "Cloudscope Multi-Simulation Complete!"
        logger  = logging.getLogger('cloudscope')

        # Attempt to send the email and catch error if unable.
        try:
            success = send_mail(recipient, subject, message)
            if success:
                logger.info("Sent notification email to {}".format(recipient))
            else:
                logger.warning("Could not send notification email to {}".format(recipient))
        except NotifyError as e:
            logger.error("Could not notify {}: {}".format(recipient, e))
