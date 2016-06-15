# tests.test_dynamo
# Tests for the dynamo sequence generators and utilities.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Nov 23 17:11:41 2015 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_dynamo.py [7298a29] benjamin@bengfort.com $

"""
Tests for the dynamo sequence generators and utilities.
"""

##########################################################################
## Imports
##########################################################################

import math
import unittest

from cloudscope.dynamo import Sequence
from cloudscope.dynamo import ExponentialSequence
from cloudscope.dynamo import CharacterSequence
from cloudscope.dynamo import NormalDistribution
from cloudscope.dynamo import UniformDistribution
from cloudscope.dynamo import BoundedNormalDistribution
from cloudscope.dynamo import DiscreteDistribution
from cloudscope.dynamo import BernoulliDistribution
from cloudscope.exceptions import UnknownType

from collections import Counter

##########################################################################
## Sequence Tests
##########################################################################

class SequenceTests(unittest.TestCase):
    """
    Make sure that the sequences behave as expected.
    """

    def test_unit_sequence(self):
        """
        Ensure an "infinite" sequence works as expected
        """
        sequence = Sequence()
        for idx in xrange(1, 100000):
            self.assertEqual(sequence.next(), idx)

    def test_step_sequence(self):
        """
        Ensure that a stepped sequence works as expected
        """
        sequence = Sequence(step=10)
        for idx in xrange(10, 100000, 10):
            self.assertEqual(sequence.next(), idx)

    def test_limit_sequence(self):
        """
        Ensure that a sequence can be limited
        """
        with self.assertRaises(StopIteration):
            sequence = Sequence(limit=1000)
            for idx in xrange(1, 100000):
                self.assertEqual(sequence.next(), idx)

    def test_reset_sequence(self):
        """
        Ensure that a sequence can be reset
        """
        sequence = Sequence()
        for idx in xrange(1, 100): sequence.next()
        self.assertGreater(sequence.value, 1)
        sequence.reset()
        self.assertEqual(sequence.next(), 1)

    def test_exponential_unit_sequence(self):
        """
        Ensure an "infinite" exponential sequence works as expected
        """
        sequence = ExponentialSequence()
        for idx in xrange(1, 1000):
            self.assertEqual(sequence.next(), 2**idx)

    def test_exponential_base_sequence(self):
        """
        Ensure that an exponential sequence with a different base works
        """
        sequence = ExponentialSequence(base=10)
        for idx in xrange(1, 1000):
            self.assertEqual(sequence.next(), 10**idx)

    def test_exponential_limit_sequence(self):
        """
        Ensure that a sequence can be limited.
        """
        with self.assertRaises(StopIteration):
            sequence = ExponentialSequence(limit=1000)
            for idx in xrange(1, 100000):
                self.assertEqual(sequence.next(), 2**idx)

    def test_reset_exponential_sequence(self):
        """
        Ensure that a sequence can be reset
        """
        sequence = ExponentialSequence()
        for idx in xrange(1, 100): sequence.next()
        self.assertGreater(sequence.value, 2)
        sequence.reset()
        self.assertEqual(sequence.next(), 2)

    @unittest.skip("Haven't figured out how to test with log yet.")
    def test_character_sequence(self):
        """
        Ensure that an "infinite" character sequence works as expected
        """
        letters = 'abcdefghijklmnopqrstuvwxyz'
        sequence = CharacterSequence()
        self.assertEqual(sequence.next(), 'a')

        for idx in xrange(1, 1000):
            val = sequence.next()
            self.assertEqual(len(val), int(math.log(idx, 26)) + 1)
            self.assertEqual(val[-1], letters[idx % 26])

    @unittest.skip("Haven't figured out how to test with log yet.")
    def test_character_sequence_upper(self):
        """
        Ensure that uppercase in the character sequence works as expected
        """
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWYZ'
        sequence = CharacterSequence(upper=True)
        self.assertEqual(sequence.next(), 'A')

        for idx in xrange(1, 1000):
            val = sequence.next()
            self.assertEqual(len(val), int(math.log(idx, 26)) + 1)
            self.assertEqual(val[-1], letters[idx % 26])

    def test_reset_character_sequence(self):
        """
        Ensure that a sequence can be reset
        """
        sequence = CharacterSequence()
        for idx in xrange(27): sequence.next()
        self.assertEqual(sequence.value, "aa")
        sequence.reset()
        self.assertEqual(sequence.next(), "a")

##########################################################################
## Distribution Tests
##########################################################################

class DistributionTests(unittest.TestCase):
    """
    Make sure that the distributions behave as expected.
    """

    def assertCloseEqual(self, first, second, amount=7, **kwargs):
        """
        Assertion for integer closeness, e.g. abs(a-b) < amount
        """
        if 'msg' not in kwargs:
            kwargs['msg'] = (
                "{} and {} are not closely equal by a difference of {}"
                .format(first, second, amount)
            )

        self.assertLessEqual(abs(first - second), amount, **kwargs)

    def test_uniform_int(self):
        """
        Weak test of uniform int distributions.
        """
        dist = UniformDistribution(10, 100)
        self.assertEqual(dist.dtype, 'int')
        for idx in xrange(100000):
            self.assertGreaterEqual(dist.next(), 10)
            self.assertLessEqual(dist.next(), 100)

    def test_uniform_float(self):
        """
        Weak test of uniform float distributions.
        """
        dist = UniformDistribution(1.0, 10.0)
        self.assertEqual(dist.dtype, 'float')
        for idx in xrange(100000):
            self.assertGreaterEqual(dist.next(), 1.0)
            self.assertLessEqual(dist.next(), 10.0)

    def test_uniform_type_detection(self):
        """
        Test type detection of uniform distribution.
        """
        self.assertEqual(UniformDistribution(1, 5).dtype, 'int')
        self.assertEqual(UniformDistribution(1.2, 5.8).dtype, 'float')

        with self.assertRaises(UnknownType):
            dist = UniformDistribution("bob", 2)

    def test_uniform_bad_type(self):
        """
        Test unknown type error in uniform distribution.
        """
        with self.assertRaises(UnknownType):
            dist = UniformDistribution(10, 12, 'bob')

        with self.assertRaises(UnknownType):
            dist = UniformDistribution(1, 21.2)

    def test_normal(self):
        """
        Weak test of normal distributions.
        """
        standard = NormalDistribution(0, 1)
        for idx in xrange(100000):
            event = standard.next()
            self.assertGreater(event, -6)
            self.assertLess(event, 6)

    def test_normal_mean(self):
        """
        Assert that the mean approximates the distribution.
        """
        dist    = NormalDistribution(0, 1)
        samples = 1000000
        total   = sum(dist.next() for idx in xrange(samples))
        mean    = total / samples

        self.assertAlmostEqual(mean, 0.0, places=2)

    def test_bounded_normal(self):
        """
        Perform same normal test with an unbounded, bounded normal.
        """
        standard = BoundedNormalDistribution(0, 1)
        for idx in xrange(100000):
            event = standard.next()
            self.assertGreater(event, -6)
            self.assertLess(event, 6)

    def test_bounded_normal_mean(self):
        """
        Perform same normal mean approximation with an unbounded, bounded normal.
        """
        dist    = BoundedNormalDistribution(0, 1)
        samples = 1000000
        total   = sum(dist.next() for idx in xrange(samples))
        mean    = total / samples

        self.assertAlmostEqual(mean, 0.0, places=2)

    def test_bounded_normal_floor(self):
        """
        Test the bounded normal with only a floor.
        """
        standard = BoundedNormalDistribution(0, 1, floor=-1)
        for idx in xrange(100000):
            event = standard.next()
            self.assertGreaterEqual(event, -1)
            self.assertLess(event, 6)

    def test_bounded_normal_ceil(self):
        """
        Test the bounded normal with only a ceil.
        """
        standard = BoundedNormalDistribution(0, 1, ceil=1)
        for idx in xrange(100000):
            event = standard.next()
            self.assertGreater(event, -6)
            self.assertLessEqual(event, 1)

    def test_bounded_normal_floor_ceil(self):
        """
        Test the bounded normal with floor and ceil.
        """
        standard = BoundedNormalDistribution(0, 1, floor=-1, ceil=1)
        for idx in xrange(100000):
            event = standard.next()
            self.assertGreaterEqual(event, -1)
            self.assertLessEqual(event, 1)

    def test_discrete_cumulative(self):
        """
        Test the creation of a cumulative distribtion.
        """
        discrete = DiscreteDistribution('abcde')
        self.assertEqual(discrete.cumulative, [1.0, 2.0, 3.0, 4.0, 5.0])

        discrete = DiscreteDistribution('abcde', [80, 5, 5, 5, 5])
        self.assertEqual(discrete.cumulative, [80, 85, 90, 95, 100])

    def test_discrete_probabilities(self):
        """
        Test the discrete probabilities computation.
        """
        discrete = DiscreteDistribution('abcde')
        self.assertEqual(
            discrete.probabilities,
            {'a':0.2, 'b':0.2, 'c':0.2, 'd':0.2, 'e':0.2}
        )

        discrete = DiscreteDistribution('abcde', [80, 5, 5, 5, 5])
        self.assertEqual(
            discrete.probabilities,
            {'a':0.8, 'b':0.05, 'c':0.05, 'd':0.05, 'e':0.05}
        )

    def test_discrete_distribution(self):
        """
        Weak test of discrete distributions.
        """
        n = 10000
        discrete = DiscreteDistribution('abcde')
        counts = Counter([discrete.get() for x in xrange(n)])
        for val, prob in discrete.probabilities.items():
            self.assertCloseEqual(counts[val], n * prob, 200)

        discrete = DiscreteDistribution('abcde', [80, 5, 5, 5, 5])
        counts = Counter([discrete.get() for x in xrange(n)])
        for val, prob in discrete.probabilities.items():
            self.assertCloseEqual(counts[val], n * prob, 200)

    def test_bernoulli_distribution(self):
        """
        Weak test of bernoulli distributions.
        """
        n = 10000
        bernoulli = BernoulliDistribution()
        self.assertAlmostEqual(bernoulli.p, 0.5)
        self.assertAlmostEqual(bernoulli.q, 0.5)

        counts = Counter([bernoulli.get() for x in xrange(n)])
        self.assertCloseEqual(counts[True], n * 0.5, 100)
        self.assertCloseEqual(counts[True], n * 0.5, 100)

        bernoulli = BernoulliDistribution(0.8)
        self.assertAlmostEqual(bernoulli.p, 0.8)
        self.assertAlmostEqual(bernoulli.q, 0.2)

        counts = Counter([bernoulli.get() for x in xrange(n)])
        self.assertCloseEqual(counts[True], n * 0.8, 100)
        self.assertCloseEqual(counts[False], n * 0.2, 100)
