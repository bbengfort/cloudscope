# cloudscope.utils.statistics
# Objects for computing Statistics and probabilities
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Thu Nov 13 13:47:15 2014 -0500
#
# Copyright (C) 2014 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: statistics.py [] benjamin@bengfort.com $

"""
Objects for computing Statistics and probabilities (reused from Ben's old code)
"""

##########################################################################
## Imports
##########################################################################

import json

from itertools import islice
from collections import Counter
from peak.util.imports import lazyModule

# Lazy loading of optional dependencies
pylab = lazyModule('pylab')

##########################################################################
## Statistical computation functions
##########################################################################

def mean(data):
    """
    TODO: if Numpy becomes a dependency, change this to a Numpy computation.
    """
    data = list(map(float, data))
    if data:
        return sum(data) / len(data)


def median(data, sort=True):
    """
    Finds the median in a list of numbers. If sort is False, this function
    expects the data to be presorted, or at least it won't be sorted again!
    Wanted to do this without the Numpy dependency, but if we bring Numpy in,
    then lets convert this function to creating a Numpy array then issuing
    the median function call.
    """
    if not data:
        return None

    num = len(data)
    if sort:
        data = sorted(data)

    if num & 1:
        # If num is odd, get the index simply by dividing it in half
        index = num / 2
        return data[index]

    # If num is even, average the two values at the center
    jdx = num / 2
    idx = jdx - 1
    return (data[idx] + data[jdx]) / 2.0


##########################################################################
## Frequency Distribution
##########################################################################

class FreqDist(Counter):
    """
    Based off of NLTK's FreqDist - this records the number of times each
    outcome of an experiment has occured. Useful for tracking metrics.
    """

    @classmethod
    def load(klass, stream):
        """
        Load a FreqDist from a dump on disk
        """
        data = json.load(stream)
        dist = klass()
        for sample, count in data.items():
            dist[sample] = count
        return dist

    def N(self):
        """
        The total number of samples that have been recorded. For unique
        samples with counts greater than zero, use B.
        """
        return sum(self.values())

    def B(self):
        """
        Return the number of sample values or bins that have counts > 0.
        """
        return len(self)

    def freq(self, key):
        """
        Returns the frequency of a sample defined as the count of the
        sample divided by the total number of outcomes. Frequencies are
        always real numbers in the range [0,1].
        """
        if self.N() == 0: return 0
        return float(self[key]) / self.N()

    def ratio(self, a, b):
        """
        Returns the ratio of two sample counts as a float.
        """
        if b not in self: return 0
        return float(self[a]) / float(self[b])

    def max(self):
        """
        Return the sample with the greatest number of outcomes.
        """
        if len(self) == 0: return None
        return self.most_common(1)[0][0]

    def plot(self, *args, **kwargs):
        """
        Plot the samples from the frequency distribution. Requires pylab.
        """

        if len(args) == 0:
            args = [len(self)]
        samples = list(islice(self, *args))

        freqs  = [self[sample] for sample in samples]
        ylabel = "Counts"

        pylab.grid(True, color="silver")
        if not "linewidth" in kwargs:
            kwargs["linewidth"] = 2

        if "title" in kwargs:
            pylab.title(kwargs["title"])
            del kwargs["title"]

        pylab.plot(freqs, **kwargs)
        pylab.xticks(range(len(samples)), [str(s) for s in samples], rotation=90)
        pylab.xlabel("Samples")
        pylab.ylabel(ylabel)

        pylab.show()

    def dump(self, stream):
        """
        Dump the collection to a JSON file on disk
        """
        json.dump(self, stream)

    def __repr__(self):
        return self.pprint()

    def pprint(self, maxlen=10):
        items = ['{0!r}: {1!r}'.format(*item) for item in self.most_common(maxlen)]
        if len(self) > maxlen:
            items.append('...')
        return 'FreqDist({{{0}}})'.format(', '.join(items))

    def __str__(self):
        return "<FreqDist with %i samples and %i outcomes>" % (self.B(), self.N())

    def __add__(self, other):
        '''Add counts from two counters.
        >>> Counter('abbb') + Counter('bcc')
        Counter({'b': 4, 'c': 2, 'a': 1})
        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = FreqDist()
        for elem in set(self) | set(other):
            newcount = self[elem] + other[elem]
            if newcount > 0:
                result[elem] = newcount
        return result

    def __sub__(self, other):
        ''' Subtract count, but keep only results with positive counts.
        >>> Counter('abbbc') - Counter('bccd')
        Counter({'b': 2, 'a': 1})
        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = FreqDist()
        for elem in set(self) | set(other):
            newcount = self[elem] - other[elem]
            if newcount > 0:
                result[elem] = newcount
        return result

    def __or__(self, other):
        '''Union is the maximum of value in either of the input counters.
        >>> Counter('abbb') | Counter('bcc')
        Counter({'b': 3, 'c': 2, 'a': 1})
        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = FreqDist()
        for elem in set(self) | set(other):
            p, q = self[elem], other[elem]
            newcount = q if p < q else p
            if newcount > 0:
                result[elem] = newcount
        return result

    def __and__(self, other):
        ''' Intersection is the minimum of corresponding counts.
        >>> Counter('abbb') & Counter('bcc')
        Counter({'b': 1})
        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = FreqDist()
        if len(self) < len(other):
            self, other = other, self
        for elem in _ifilter(self.__contains__, other):
            p, q = self[elem], other[elem]
            newcount = p if p < q else q
            if newcount > 0:
                result[elem] = newcount
        return result
