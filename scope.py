#!/usr/bin/env python
# scope
# Management and administration script for CloudScope
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sat Jan 09 10:03:40 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: scope.py [] benjamin@bengfort.com $

"""
Management and administration script for CloudScope
"""

##########################################################################
## Imports
##########################################################################

import argparse
import cloudscope

from cloudscope.server import CloudScopeWebServer
from cloudscope.simulation.cars import GasStationSimulation

##########################################################################
## Command Variables
##########################################################################

DESCRIPTION = "Management and administration commands for CloudScope"
EPILOG      = "If there are any bugs or concerns, submit an issue on Github"
VERSION     = cloudscope.get_version()


##########################################################################
## Commands
##########################################################################

def serve(args):
    httpd = CloudScopeWebServer()
    httpd.run()
    return ""


def simulate(args):
    sim = GasStationSimulation()
    sim.run()

    # Dump the output data to a file.
    if args.output is None:
        path = "{}-{}.json".format(sim.name, sim.results.finished.strftime('%Y%m%d'))
        args.output = open(path, 'w')
    sim.results.dump(args.output)

    return "Results for {} written to {}".format(sim.name, args.output.name)

##########################################################################
## Main Function and Methodology
##########################################################################

def main(*args):

    # Construct the argument parser
    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG, version=VERSION)
    subparsers = parser.add_subparsers(title='commands', description='CloudScope administration commands.')

    # Serve Command
    serve_parser = subparsers.add_parser('serve', help='a simple development/debugging web server.')
    serve_parser.set_defaults(func=serve)

    # Simulate Command
    sim_parser = subparsers.add_parser('simulate', help='run the simulation with the given configuration.')
    sim_parser.add_argument('-o', '--output', type= argparse.FileType('w'), default=None, metavar= 'PATH', help='specify location to write output to')
    sim_parser.set_defaults(func=simulate)

    # Handle input from the command line
    args = parser.parse_args()            # Parse the arguments
    try:
        msg = args.func(args)             # Call the default function
        parser.exit(0, msg+"\n")          # Exit cleanly with message
    except Exception as e:
        parser.error(str(e))              # Exit with error

if __name__ == '__main__':
    main()
