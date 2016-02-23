# cloudscope.replica.consensus.election
# Data structures for handling elections and election timeouts.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Feb 19 09:53:35 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: election.py [] benjamin@bengfort.com $

"""
Data structures for handling elections and election timeouts.
"""

##########################################################################
## Imports
##########################################################################

from cloudscope.dynamo import Uniform
from cloudscope.config import settings
from cloudscope.simulation.timer import Timer

##########################################################################
## Election Timer
##########################################################################

class ElectionTimer(Timer):
    """
    Specialized Timer for handling elections, primarily by randomizing the
    amount of time until the next event occurs (so as followers don't become
    candidates at the exact sime time).
    """

    ELECTION_TIMEOUT = settings.simulation.election_timeout

    @classmethod
    def fromReplica(klass, replica, delay=ELECTION_TIMEOUT):
        """
        Instantiates an election timer from a replica's environment.
        """
        return klass(replica.env, delay, replica.on_election_timeout)

    @property
    def delay(self):
        """
        Computes a random delay from the election timeout range.
        """
        return self._delay.get()

    @delay.setter
    def delay(self, delay):
        """
        Creates a uniform distribution based on a delay range.
        """
        self._delay = Uniform(*delay)


##########################################################################
## Election
##########################################################################

class Election(object):
    """
    A simple container that keeps track of an election and determines the
    winner of an election by majority. The ballot is a simple yes/no vote.
    """

    def __init__(self, quorum=None):
        # Establish a quorum of voters
        self.quorum = {}

        # Add initial None votes to those who haven't voted yet.
        if quorum is not None:
            # Ensure all members of the quorum are added
            for voter in quorum:
                self.quorum[voter] = None

    @property
    def n_majority(self):
        """
        Computes the number of votes required for a majority vote.
        """
        # Majority is integer division by 2 + 1.
        return (len(self.quorum) / 2) + 1

    def vote(self, voter, vote=True):
        """
        Register a vote, usually an affirmative vote.
        """
        self.quorum[voter] = vote

    def has_quorum(self):
        """
        Enough votes, either True or False have been passed (a majority).
        """
        notnone = lambda v: v is not None
        return len(filter(notnone, self.quorum.values())) >= self.n_majority

    def has_passed(self):
        """
        Decide if the number of True votes is a majority.
        """
        yeas = lambda v: v is True
        return len(filter(yeas, self.quorum.values())) >= self.n_majority

    def has_failed(self):
        """
        Decide if the number of False votes is a majority.
        """
        nos = lambda v: v is False
        return len(filter(nos, self.quorum.values())) >= self.n_majority
