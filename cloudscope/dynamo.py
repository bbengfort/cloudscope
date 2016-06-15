# cloudscope.dynamo
# These utilities are "generators" e.g. classes that produce things.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Mon Nov 23 16:46:34 2015 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: dynamo.py [d0f0ca1] benjamin@bengfort.com $

"""
These utilities are "generators" e.g. classes that produce things. These are
the essential tools for generating events in the system particularly random
events or other sequences that we will use in our processes.
"""

##########################################################################
## Imports
##########################################################################

import string
import bisect
import random
import itertools

from cloudscope.viz import plot_kde
from cloudscope.viz import plot_time
from cloudscope.config import settings
from cloudscope.exceptions import UnknownType

##########################################################################
## Base Dynamo
##########################################################################


class Dynamo(object):
    """
    A dynamo is a numeric generator for use in our simulation. Right now this
    simply exposes the standard interface for a Python iterator, but may do
    more in the future.
    """

    def next(self):
        raise NotImplementedError("Dynamos must have a next method.")

    def __iter__(self):
        return self

##########################################################################
## Sequences
##########################################################################


class Sequence(Dynamo):
    """
    An infinite sequence and counter object.
    This is a bit more logic than exposed by `itertools.count()`
    Note that unlike xrange, start is never yielded, and the limit is
    inclusive, e.g. the range in a sequence is (start, limit]
    """

    def __init__(self, start=0, limit=None, step=1):
        self.value = start
        self.step  = step
        self.limit = limit

    def next(self):
        self.value += self.step

        if self.limit is not None and self.value > self.limit:
            raise StopIteration("Stepped beyond limit value!")

        return self.value

    def reset(self):
        """
        Resets the value back to zero
        """
        self.value = 0


class ExponentialSequence(Sequence):
    """
    An infinite exponential sequence (for funsies).
    """

    def __init__(self, start=0, base=2, limit=None):
        self.base  = base
        self.power = start
        self.limit = limit

    @property
    def value(self):
        return self.base ** self.power

    def next(self):
        self.power += 1

        if self.limit is not None and self.value > self.limit:
            raise StopIteration("Exponential ceiling reached!")

        return self.value

    def reset(self):
        """
        Resets the power back to zero
        """
        self.power = 0


class CharacterSequence(Sequence):
    """
    An infinite sequence of ASCII characters a-z, aa-zz, aaa-zzz, etc.
    """

    def __init__(self, chars=string.ascii_lowercase, upper=False, limit=None):
        self.chars = chars.upper() if upper else chars
        self.limit = limit.upper() if upper and limit else limit
        self.wheel = self.character_products()
        self.value = ""

        if not self.chars:
            raise UnknownType("No characters passed in for sequence!")

    def next(self):
        self.value = self.wheel.next()

        if self.limit is not None and self.value == self.limit:
            raise StopIteration("Character ceiling reached!")

        return self.value

    def character_products(self):
        """
        Internal function to make the generator.
        """
        for i in itertools.count(1):
            for product in itertools.product(self.chars, repeat=i):
                yield "".join(product)

    def reset(self):
        """
        Resets the value back to zero
        """
        self.value = ""
        self.wheel = self.character_products()

##########################################################################
## Distributions
##########################################################################


class Distribution(Dynamo):
    """
    A Distribution is a Dynamo (an iterator that generates numbers) but
    because it models random samples, a `get` method is aliased to `next`.
    """

    def get(self):
        return self.next()

    def plot(self, n=100, **kwargs):
        """
        Vizualizes the density estimate of the distribution.
        """
        title = kwargs.pop('title',
            '{} Distribution Plot'.format(
            self.__class__.__name__.rstrip('Distribution')
        ))

        random.seed(kwargs.pop('random_seed', settings.simulation.random_seed))
        series = [self.get() for x in xrange(n)]
        axe = plot_kde(series, **kwargs)

        axe.set_ylabel('frequency')
        axe.set_xlabel('value')
        axe.set_title(title)

        return axe


class UniformDistribution(Distribution):
    """
    Generates uniformly distributed values inside of a range. Basically a
    wrapper around `random.randint` and `random.uniform` depending on type.
    """

    def __init__(self, minval, maxval, dtype=None):
        # Detect type from minval and maxval
        if dtype is None:
            if isinstance(minval, int) and isinstance(maxval, int):
                dtype = 'int'
            elif isinstance(minval, float) and isinstance(maxval, float):
                dtype = 'float'
            else:
                raise UnknownType(
                    "Could not detect type from range {!r} to {!r}"
                    .format(minval, maxval)
                )

        # If dtype is given, validate it from given choices.
        if dtype not in {'int', 'float'}:
            raise UnknownType(
                "{!r} is not a valid type, use int or float".format(dtype)
            )

        self.range = (minval, maxval)
        self.dtype = dtype

    def next(self):
        jump = {
            'int': random.randint,
            'float': random.uniform,
        }

        return jump[self.dtype](*self.range)


## Alias for Uniform Distribution
Uniform = UniformDistribution


class NormalDistribution(Distribution):
    """
    Generates normally distributed values
    """

    def __init__(self, mean, stddev):
        self.mean  = mean
        self.sigma = stddev

    def next(self):
        return random.gauss(self.mean, self.sigma)


## Alias for Normal Distribution
Normal = NormalDistribution


class BoundedNormalDistribution(NormalDistribution):
    """
    A normal distribution with a hard floor and/or ceiling.
    """

    def __init__(self, mean, stddev, floor=None, ceil=None):
        self.floor = floor
        self.ceil  = ceil
        super(BoundedNormalDistribution, self).__init__(mean, stddev)

    def next(self):
        val = super(BoundedNormalDistribution, self).next()
        if self.floor is not None:
            val = max(val, self.floor)

        if self.ceil is not None:
            val = min(val, self.ceil)

        return val


## Alias for Bounded Normal Distribution
BoundedNormal = BoundedNormalDistribution


class DiscreteDistribution(Distribution):
    """
    Generates a random selection from a possible list of values, and is
    basically a wrapper for `random.choice`. By default each possible outcome
    has a uniform probability, however weights can be supplied as an
    extra list to change the distribution properties.
    """

    def __init__(self, values, weights=None):
        if weights is None:
            weights = [1 for _ in xrange(len(values))]

        self.values  = values
        self.weights = map(float, weights)

        # Create a cumulative distribution
        self.total = 0.0
        self.cumulative = []

        for w in weights:
            self.total += w
            self.cumulative.append(self.total)

    @property
    def probabilities(self):
        return dict([
            (value, self.weights[idx] / self.total)
            for idx, value in enumerate(self.values)
        ])

    def next(self):
        x = random.random() * self.total
        i = bisect.bisect(self.cumulative, x)
        return self.values[i]

## Alias for Discrete Distribution
Discrete = DiscreteDistribution


class BernoulliDistribution(Distribution):
    """
    The probability distribution of a random variable which is True with the
    success probability of p and False with the probability of 1-p. By default
    this is a coin toss with probability p=0.5.
    """

    def __init__(self, p=0.5):
        self.p = p
        self.q = 1 - p

    def next(self):
        return random.random() < self.p

## Alias for Bernoulli Distribution
Bernoulli = BernoulliDistribution
