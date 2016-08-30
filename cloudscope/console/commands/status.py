# cloudscope.console.command.status
# Checks on the status of a multisim command by reviewing log messages.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Aug 30 11:58:12 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: status.py [] benjamin@bengfort.com $

"""
Checks on the status of a multisim command by reviewing log messages.
"""

##########################################################################
## Imports
##########################################################################

import re
import argparse

from commis import Command
from datetime import datetime
from collections import Counter, namedtuple

##########################################################################
## Regex
##########################################################################

STARTED  = re.compile(r'^\[([\w\d\:\s\/]+)\] INFO Starting simulation (\d+): "(.+)"$')
FINISHED = re.compile(r'^\[([\w\d\:\s\/]+)\] INFO Simulation (\d+): "(.+)" completed in ([\w\d\s]+)$')
ERRORED  = re.compile(r'^\[([\w\d\:\s\/]+)\] ERROR Simulation (\d+) \((.+)\) errored: (.+)$')


##########################################################################
## Row Parsing
##########################################################################

DATEFMT  = "%d/%b/%Y %H:%M:%S"
Started  = namedtuple('Started', 'timestamp, index, name')
Finished = namedtuple('Finished', 'timestamp, index, name, delta')
Errored  = namedtuple('Errored', 'timestamp, index, path, error')

##########################################################################
## Command
##########################################################################

class StatusCommand(Command):

    name = 'status'
    help = 'inspect a multisim log file to see how far it is'
    args = {
        'log': {
            'type': argparse.FileType('r'),
            'nargs': '+',
            'help': 'the logfile (usually nohup.out) to read the status from',
        }
    }

    def handle(self, args):
        """
        Uses regular expressions to parse the log file for jobs.
        """

        started  = Counter()
        finished = Counter()
        errored  = 0
        unparsed = 0

        for log in args.log:
            for line in log:
                row = self.parse(line)

                if isinstance(row, Started):
                    started[row.name] += 1

                elif isinstance(row, Finished):
                    finished[row.name] += 1

                elif isinstance(row, Errored):
                    errored += 1

                else:
                    unparsed += 1

        n_started  = sum(started.values())
        n_finished = sum(finished.values()) + errored

        output = [
            "{} finished out of {} started ({} errors)".format(n_finished, n_started, errored),
            "",
        ]

        for name, c_started in started.items():
            c_finished = finished.get(name, 0)
            output.append(
                "{: >3}/{: <3} {}".format(c_finished, c_started, name)
            )

        if unparsed:
            output.append("")
            output.append("Could not parse {} lines in the log file!".format(unparsed))

        return "\n".join(output)


    def parse(self, line):
        """
        Parses a line using the regular expressions returning a named tuple
        or None if the line could not be parsed.
        """

        line  = line.strip()
        regex = (STARTED, FINISHED, ERRORED)
        types = (Started, Finished, Errored)

        for regex, klass in zip(regex, types):
            match = regex.match(line)
            if match:
                row = list(match.groups())
                row[0] = datetime.strptime(row[0], DATEFMT)
                return klass(*row)

        return None
