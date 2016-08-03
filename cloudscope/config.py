# cloudscope.config
# Configuration for the CloudScope project.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Thu Jan 07 16:13:49 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: config.py [2a66be9] benjamin@bengfort.com $

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


class NotifyConfiguration(Configuration):
    """
    Email settings so that CloudScope can send email messages
    """

    username    = None
    password    = None
    email_host  = None
    email_port  = None
    fail_silent = True


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
    count_messages       = True
    aggregate_heartbeats = True
    default_latency      = 800
    default_replica      = "storage"
    default_consistency  = "strong"

    # Workload Parameters
    users                = 1     # number of simulated users creating traces
    max_users_location   = None  # limit the number of users per location
    max_objects_accessed = 1     # maximum number of objects that can be accessed (per user)
    synchronous_access   = False # each access has to wait on the previous access to be triggered

    # Locations to allow users to move to
    invalid_locations = [
        "cloud",
    ]

    # Replica types that shouldn't have accesses.
    invalid_types   = [
        "backup",
    ]

    conflict_prob   = 0.0     # probability of object overlap and potential access conflict
    move_prob       = 0.2     # probability of moving locations
    switch_prob     = 0.3     # probability of switching devices
    object_prob     = 0.3     # probability of switching the currently accessed object
    access_mean     = 1800    # mean delay between accesses (milliseconds)
    access_stddev   = 512     # stddev of delay between accesses (milliseconds)
    read_prob       = 0.6     # probability of read access (write is 1-read_prob)

    # Integration parameter: default, floated, or federated
    integration     = "default"

    # Eventual Parameters
    anti_entropy_delay = 600  # delay in milliseconds (20x per minute)
    do_gossip   = True        # perform gossip protocol
    do_rumoring = False       # perform rumor mongering

    # Raft Parameters
    election_timeout   = [150, 300]
    heartbeat_interval = 75     # Usually half the minimum election timeout
    aggregate_writes   = False  # Don't send writes until heartbeat.

    # Tag Parameters
    session_timeout    = 4096 # Related to the mean delay between accesses

    # Federated Parameters
    sync_prob  = 0.3  # probability of eventual syncing with core consensus
    local_prob = 0.6  # probability of local anti-entropy over wide area (wide area is 1-local_prob)

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

    # Notification parameters
    notify     = NotifyConfiguration()

    # Visualization parameters
    vizualization = VisualizationConfiguration()

##########################################################################
## Generate Site Settings
##########################################################################

settings = CloudScopeConfiguration.load()

if __name__ == '__main__':
    print settings
