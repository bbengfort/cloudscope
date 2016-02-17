# cloudscope.config
# Configuration for the CloudScope project.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Jan 07 16:13:49 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: config.py [] benjamin@bengfort.com $

"""
Configuration for the CloudScope project.
"""

##########################################################################
## Imports
##########################################################################

import os

from confire import Configuration

##########################################################################
## Base Paths
##########################################################################

PROJECT  = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


##########################################################################
## Web Configurations
##########################################################################

class SiteConfiguration(Configuration):
    """
    Configuration variables to add to the site.
    """

    htdocs      = os.path.join(PROJECT, "deploy")
    url         = "http://localhost:8080"
    title       = "CloudScope"
    author      = "Benjamin  Bengfort"
    keywords    = "Distributed Storage Systems, Visualization, Simulation"
    description = "Visualization of distributed systems and communications."


class ServerConfiguration(Configuration):
    """
    Configure the development server
    """

    address     = "localhost"
    port        = 8080


##########################################################################
## Logging Configuration
##########################################################################

class LoggingConfiguration(Configuration):
    """
    Very specific logging configuration instructions (does not provide the
    complete configuration as available in the python logging module). See
    the `cloudscope.utils.logger` module for more info.
    """

    level   = "INFO"
    logfmt  = "[%(asctime)s] %(levelname)s %(message)s"
    datefmt = "%d/%b/%Y %H:%M:%S"
    disable_existing_loggers = False


##########################################################################
## Simulation Configuration
##########################################################################

class SimulationConfiguration(Configuration):

    # Simulation Environment Parameters
    random_seed     = 42
    max_sim_time    = 4320000

    # Network Parameters
    default_latency = 800
    default_replica = "storage"
    default_consistency = "strong"

    # Workload Parameters
    # Locations to allow users to move to
    valid_locations = [
        "home", "work", "mobile"
    ]

    # Replica types that shouldn't have accesses.
    invalid_types   = [
        "storage"
    ]

    move_prob       = 0.2     # probability of moving locations
    switch_prob     = 0.4     # probability of swithcing devices
    access_mean     = 1800    # mean delay between accesses (milliseconds)
    access_stddev   = 512     # stddev of delay between accesses (milliseconds)
    read_prob       = 0.8     # probability of read access (write is 1-read_prob)

    # Eventual Parameters
    anti_entropy_delay = 3000 # delay in milliseconds (20x per minute)
    do_gossip   = True        # perform gossip protocol
    do_rumoring = True        # perform rumor mongering

    # Raft Parameters
    election_timeout   = [150, 300]
    heartbeat_interval = 75  # Usually half the minimum election timeout


class VisualizationConfiguration(Configuration):

    style         = "whitegrid"
    context       = "paper"
    palette       = None


##########################################################################
## Application Configuration
##########################################################################

class CloudScopeConfiguration(Configuration):

    CONF_PATHS = [
        '/etc/cloudscope.yaml',
        os.path.expanduser('~/.cloudscope.yaml'),
        os.path.abspath('conf/cloudscope.yaml')
    ]

    debug      = False
    testing    = True
    logging    = LoggingConfiguration()

    # Web server parameters
    site       = SiteConfiguration()
    server     = ServerConfiguration()

    # Simulation parameters
    simulation = SimulationConfiguration()

    # Visualization parameters
    vizualization = VisualizationConfiguration()

##########################################################################
## Generate Site Settings
##########################################################################

settings = CloudScopeConfiguration.load()

if __name__ == '__main__':
    print settings
