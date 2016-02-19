# tests.test_simulation.test_replica.test_consensus.test_election
# Testing the data structures and helpers for an election.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Fri Feb 19 10:10:24 2016 -0500
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_election.py [] benjamin@bengfort.com $

"""
Testing the data structures and helpers for an election.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.simulation.replica.consensus.election import Election

##########################################################################
## TestCase
##########################################################################

class ElectionTests(unittest.TestCase):

    def test_quorum_majority(self):
        """
        Test that the quorum majority is correct
        """
        ballots = Election('abcdef')
        self.assertEqual(ballots.n_majority, 4, 'Even quorum majority computation failed')

        ballots = Election('abcdefg')
        self.assertEqual(ballots.n_majority, 4, 'Odd quorum majority computation failed')

    def test_election_quorum(self):
        """
        Test that an election stays incomplete until a majority of votes
        """
        votes = Election('abcdef')
        for idx, char in enumerate('abc'):
            votes.vote(char, idx % 2 == 0)
            self.assertFalse(votes.has_quorum())

        for idx, char in enumerate('def'):
            votes.vote(char, idx % 2 == 0)
            self.assertTrue(votes.has_quorum())

    def test_election_passed(self):
        """
        Test that an election passes after quorum
        """
        votes = Election('abcdef')
        for idx, char in enumerate('abc'):
            votes.vote(char, idx % 2 == 0)
            self.assertFalse(votes.has_passed())

        for idx, char in enumerate('def'):
            votes.vote(char, idx % 2 == 0)

        self.assertTrue(votes.has_passed())

    def test_election_failed(self):
        """
        Test that an election fails after quorum
        """
        votes = Election('abcdef')
        for idx, char in enumerate('abc'):
            votes.vote(char, idx % 2 != 0)
            self.assertFalse(votes.has_failed())

        for idx, char in enumerate('def'):
            votes.vote(char, idx % 2 != 0)

        self.assertTrue(votes.has_failed())
