# tests.test_utils.test_statistics
# Testing for the statistics utility module.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Aug 23 13:40:49 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_statistics.py [736a559] benjamin@bengfort.com $

"""
Testing for the statistics utility module.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from itertools import product
from cloudscope.utils.statistics import *


##########################################################################
## Fixtures
##########################################################################

# Empty test case
EMPTY = []

# Float test cases
FLOATS = [
    # Uniform random [0.0, 1.0)
    [ 0.43730873,  0.66860239,  0.34969353,  0.64048078,  0.06388402,
      0.27340017,  0.77561069,  0.0469865 ,  0.00952501,  0.905221  ,
      0.85934168,  0.81024019,  0.06976906,  0.54518943,  0.27677394,
      0.12399665,  0.43676722,  0.5155873 ,  0.38699299,  0.76616917,
      0.02502538,  0.40382399,  0.99043387,  0.71853195,  0.42132248,
      0.23079655,  0.12753139,  0.72196278,  0.63156918,  0.58127711,
      0.323632  ,  0.75723769,  0.55014024,  0.48530899,  0.81193682,
      0.63641341,  0.9896141 ,  0.59410421,  0.08999124,  0.44973318,
      0.20534478,  0.35249505,  0.68384246,  0.10588445,  0.81486703,
      0.82123886,  0.23312338,  0.29706749,  0.95132877,  0.53760118,
      0.52506907,  0.18586977,  0.10429846,  0.37754277,  0.80177148,
      0.8923954 ,  0.01853723,  0.32609851,  0.83528495,  0.59851704,
      0.94780306,  0.00333868,  0.64453206,  0.68733814,  0.69465826,
      0.17311021,  0.81104648,  0.36074105,  0.86521824,  0.57384475,
      0.54296227,  0.95244882,  0.4340912 ,  0.79415668,  0.36713392,
      0.01035679,  0.37757458,  0.86641362,  0.24478224,  0.48594984,
      0.16053626,  0.4092285 ,  0.52627802,  0.12932203,  0.49634128,
      0.69001666,  0.62750143,  0.22644635,  0.61771225,  0.26848362,
      0.38573517,  0.82619298,  0.4761255 ,  0.60803911,  0.25304987,
      0.30113422,  0.57631252,  0.66860624,  0.23604634,  0.21473307 ],

    # Uniform random [0.0, 100.0]
    [ 22.20520866,  17.17258577,   8.49659732,  13.95346708,
      55.55125426,   8.80317998,  24.68324592,  96.84491714,
      22.72401521,  73.64288806,  42.17152252,  14.37810073,
      34.24014255,  60.81097632,  59.87367563,  52.2406963 ,
       6.49507369,  39.25094041,  72.35007601,  94.3952359 ,
      28.06879455,  39.47692788,  13.88718282,   6.97516371,
      66.55848707,  31.92083665,  25.32500032,  56.42714507,
       7.51769482,  28.60784098,  24.08155829,  89.91651969,
      47.86004113,  71.85761032,  82.4294561 ,  68.91388351,
       4.44603844,  42.60146732,  64.99026944,  11.28079872,
      89.95259469,  21.62473926,  40.67768745,  74.03776227,
      47.28452248,  42.43533983,   4.54809125,  64.33809063,
       0.48360149,  53.58079114,  71.05946081,  68.42234587,
      70.6191961 ,  89.55513029,  23.68983622,  46.13571428,
      95.80340964,  31.05251035,  18.16043837,  85.30237868,
      34.85336423,  85.13625608,  33.24675386,  65.98221573,
      43.41008904,   1.41689122,  25.66436842,  97.83154993,
      28.95244763,  58.6737343 ,  31.11425024,  39.89891167,
      18.87817841,  63.74118985,   7.34593289,  11.56234643,
      70.74670506,  94.08037005,  20.42316914,  46.72559006,
      41.20221363,  81.16258525,  83.10004094,  22.6069545 ,
      46.25125172,  19.02403741,  41.4161593 ,  17.98574115,
      83.66625755,  66.30583531,  74.77229409,  81.07751229,
       6.00914795,  18.30008296,  37.99743388,  23.08334708,
      36.67738259,  28.58053073,  76.88689287,  88.09260102 ],

    # Normal random gaussian distribution with mean=0 and sigma=1
    [ 1.36628297, -0.95063669, -0.7409544 ,  0.49168896,  0.64369943,
       -1.36683641, -0.85050743,  0.14056131,  0.40071956,  0.06894656,
       -0.35099341, -0.94658349, -0.05191993, -0.68728832,  1.5290626 ,
       -0.29765041, -1.47736747,  1.42462537, -0.93737476, -1.75120617,
        0.37956676, -0.41298492,  1.26101492, -1.11693991,  0.86228129,
        1.25771588, -1.698729  , -0.34431668, -0.34907691,  1.52828139,
       -1.65994198, -1.22920884, -1.416939  ,  0.4581475 ,  0.25962794,
       -1.10938565, -2.01038612, -0.89623881, -0.02473882, -0.10925982,
        1.49019119, -0.71829783, -0.57516934,  1.31854532,  0.64051439,
       -0.539811  , -0.36544998,  0.34168854,  1.03403893,  0.1788948 ,
        0.3961166 , -2.04685416, -0.50117633,  0.72760044, -1.23274552,
       -0.34341958, -0.75571399,  1.39371562, -0.01919108, -0.17840926,
        0.27388972,  0.81694269,  0.19208915, -0.90984528, -0.43602705,
       -1.9333356 , -0.82054677, -0.22563851,  0.38139457,  0.35015976,
        0.70850311, -0.24979133, -0.83115026, -0.22170927, -1.47006649,
       -1.42263061,  2.67703557, -0.4531137 , -0.01348267, -0.1477644 ,
       -0.59528241, -0.99513121, -0.19154543,  1.3695901 , -0.40227537,
        1.37180334,  0.52361872, -0.09802685,  1.70726494, -0.28957362,
        2.12909179,  0.91799377,  0.75537678,  0.35040934, -0.20546863,
        1.70405968,  0.96502427,  0.81638739,  1.88802825,  1.06889865 ],

    # Normal random gaussian distribution with mean=100 and sigma=18
    [  97.15759554,   77.17442118,  121.65339951,  115.47590292,
         83.13049538,   80.58906683,  133.28962059,  101.19894129,
        102.23057183,   92.82933217,   96.243821  ,   97.2783628 ,
         99.62594213,  119.51777017,  141.770821  ,  111.48806454,
         87.59254024,   92.02257259,   87.26595797,  106.22640402,
        120.33377392,   80.79363771,   85.66117399,   62.35418484,
        135.02835057,  128.33176531,  105.24356978,  125.16042398,
         84.50687617,   99.95500342,  102.14580588,  129.78867181,
        130.95831888,  107.58328424,   78.38888971,   85.59218946,
        132.50719329,   82.13758304,  100.1639717 ,   80.05534368,
         91.68220069,   86.70158004,   88.42494344,   92.22226738,
         93.75785656,   95.36178327,   85.2791005 ,   88.03325987,
        100.78703198,  136.73102739,   92.70148723,  115.0907645 ,
        120.05135927,  100.12796585,   70.13846055,  136.07669925,
         97.44144139,  109.51705036,   99.31486862,  111.37134817,
         78.430312  ,  114.61626988,  103.06188281,   55.51858758,
        104.55853914,  126.27837134,   91.4791138 ,   91.74949264,
         99.45526277,   60.83926795,   73.31706548,  109.1869211 ,
         92.71997445,   92.29068272,   69.76686038,   96.69493926,
         98.98031343,  105.2876436 ,  124.74573867,  123.59994673,
        114.99458381,   93.90003085,   89.68415181,  135.73404241,
        112.74098956,  118.8758599 ,   77.30905375,   83.08948144,
        123.81454249,   95.22466886,   79.00660774,   87.19579895,
        105.46176326,  110.65034971,   95.13515247,   62.24700869,
         88.66132196,   90.00716862,  107.83890058,   97.73738434],
]

# Integer test cases
INTEGERS = [
    # Between 1 and 10
    [7, 6, 1, 1, 7, 3, 9, 5, 7, 6, 3, 1, 5, 3, 9, 5, 1, 8, 1, 2, 2, 2, 5,
     2, 1, 6, 8, 5, 8, 4, 7, 8, 3, 3, 7, 4, 4, 4, 7, 5, 5, 9, 2, 6, 6, 6,
     1, 4, 7, 1, 6, 6, 6, 5, 5, 6, 9, 5, 7, 6, 5, 6, 3, 8, 9, 9, 6, 6, 2,
     1, 3, 1, 6, 2, 7, 4, 3, 6, 7, 3, 4, 2, 9, 2, 4, 4, 9, 5, 5, 5, 4, 7,
     5, 4, 2, 4, 7, 3, 8, 1, 8, 1, 9, 7, 6, 4, 4, 1, 3, 6, 9, 1, 1, 5, 6],

    # Between 10 and 500
    [128, 142, 351, 128, 436, 451,  28, 416, 204, 194, 429,  33,  55,
     122, 305, 466, 293, 386, 203, 201, 194, 288, 184,  15, 486,  39,
     419, 311, 190, 101, 164,  79,  16, 206, 176,  74, 189,  12,  77,
     182, 296, 280, 169, 282, 415, 108, 407,  11, 268, 135, 356, 326,
     312, 294, 225, 406, 172, 331, 196, 266,  80, 406, 388, 205, 401,
     421, 224, 106,  45, 247, 200, 201, 451, 205, 179, 279, 172,  30,
     216, 236,  56, 323, 206,  14, 383, 211, 106,  24,  60, 210,  36,
      83, 348, 276, 397, 415,  32,  58,  15, 224, 379, 248, 166, 450,
     161,  74, 306, 412, 471, 108, 169, 157,  75,  59,  14, 295, 390],

    # Bits (1s and 0s)
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1,
     0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1,
     0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1,
     1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0,
     1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0],

     # With negative numbers (between -10 and 10)
    [-10,   8,   0,   0,  -5,   6,  -1,   2, -10,  -4,  -5,   1,   8,
      -7,   2,  -2,  -5,   5,   5,  -5,  -6,  -1,  -1,   5,   9,   1,
       1, -10,   9,   5,  -7,   7,   8,  -1,  -5,  -5,   3,  -7,   8,
      -2,   6,  -6,   0,  -9,  -7, -10,  -2,   5,  -8,  -9,   7,  -9,
      -6,   4,  -2,  -8,  -7,   2,  -3,   8,  -1,   9,   7,   4,  -3,
       8,   3,  -5,   4,  -5, -10,  -8,   3,  -9,  -9,  -6,  -3,   2,
      -6, -10,  -6,   8,  -4, -10,   4,  -8,  -6,  -3,  -8,   6,   2,
      -5,   6,   2,   0,  -4,  -2,  -8,  -7,   5,   6,   9,   9,   4,
       5,   8,   3,  -9,  -6,   7,  -1,   6,  -5,   1,  -2,  -7,   0],
]

##########################################################################
## Statistics Tests
##########################################################################

class StatisticsTests(unittest.TestCase):
    """
    Test cases for the statistics helper functions
    """

    def test_mean_edge_cases(self):
        """
        Test any edge cases that are passed to mean.
        """
        self.assertEqual(mean(EMPTY), None)
        self.assertEqual(mean(None), None)

    def test_mean_integers(self):
        """
        Test mean on integers returns correct float
        """

        # Computed using numpy
        expected = [
            4.8260869565217392, 219.92307692307693,
            0.47826086956521741, -0.89743589743589747
        ]

        for idx, data in enumerate(INTEGERS):
            mu = mean(data)
            self.assertIsInstance(mu, float)
            self.assertEqual(mu, expected[idx])

    def test_mean_floats(self):
        """
        Test mean on floats returns correct float
        """

        # Computed using numpy
        expected = [
            0.48705447450000006, 45.260727738500009,
            -0.014150190199999982, 99.931501583200003
        ]

        for idx, data in enumerate(FLOATS):
            mu = mean(data)
            self.assertIsInstance(mu, float)
            self.assertAlmostEqual(mu, expected[idx])

    def test_median_edge_cases(self):
        """
        Test any edge cases that are passed to median.
        """
        self.assertEqual(median(EMPTY), None)
        self.assertEqual(median(None), None)

    def test_median_integers(self):
        """
        Test median on integers returns correct float
        """

        # Computed using numpy
        expected = [5, 204, 0, -1]

        for idx, data in enumerate(INTEGERS):
            mu = median(data)
            self.assertIsInstance(mu, int)
            self.assertEqual(mu, expected[idx])

    def test_median_floats(self):
        """
        Test median on floats returns correct float
        """

        # Computed using numpy
        expected = [
            0.49114555999999998, 41.309186464999996,
            -0.12851210999999998, 97.589412865
        ]

        for idx, data in enumerate(FLOATS):
            mu = median(data)
            self.assertIsInstance(mu, float)
            self.assertAlmostEqual(mu, expected[idx])

    def test_median_even_integers(self):
        """
        Test median on an even lengthed list of integers
        """
        cases = [
            [5, 6, 9, 6, 7, 2, 5, 5, 5, 3],
            [6, 1, 6, 7, 2, 1, 4, 9, 2, 8, 3, 8, 7, 5],
            [6, 5, 6, 1, 5, 1, 6, 8, 2, 6, 8, 5, 5, 2, 1, 8, 1, 7]
        ]

        # Computed using numpy
        expected = [5.0, 5.5, 5.0]

        for case, expect in zip(cases, expected):
            mu = median(case)
            self.assertIsInstance(mu, float)
            self.assertEqual(expect, mu)


##########################################################################
## Online Variance Tests
##########################################################################

class OnlineVarianceTests(unittest.TestCase):
    """
    Test cases for the OnlineVariance class
    """

    def test_mean_edge_cases(self):
        """
        Test any edge cases that are passed to mean.
        """
        online = OnlineVariance()

        # Test the case of no samples
        self.assertEqual(online.mean, 0.0)
        self.assertEqual(online.std, 0.0)
        self.assertEqual(online.var, 0.0)

        # Test the case of one sample
        online.update(42)

        self.assertEqual(online.mean, 42.0)
        self.assertEqual(online.std, 0.0)
        self.assertEqual(online.var, 0.0)

    def test_online_variance_length(self):
        """
        Test that the length of an online variance is the number of samples.
        """
        cases    = INTEGERS + FLOATS
        expected = [115,117,115,117,100,100,100,100]

        for data, case in zip(cases, expected):
            online = OnlineVariance()
            self.assertEqual(len(online), 0)
            for item in data:
                online.update(item)

            self.assertEqual(len(online), case)

    def test_online_integers_mean(self):
        """
        Test online variance computing means on integers
        """

        # Computed using numpy
        expected = [
            4.8260869565217392, 219.92307692307693,
            0.47826086956521741, -0.89743589743589747
        ]

        for data, case in zip(INTEGERS, expected):
            online = OnlineVariance()
            self.assertEqual(online.mean, 0.0)
            for item in data:
                online.update(item)

            self.assertIsInstance(online.mean, float)
            self.assertEqual(online.mean, case)

    def test_online_float_mean(self):
        """
        Test online variance computing means on floats.
        """

        # Computed using numpy
        expected = [
            0.48705447450000006, 45.260727738500009,
            -0.014150190199999982, 99.931501583200003
        ]

        for data, case in zip(FLOATS, expected):
            online = OnlineVariance()
            self.assertEqual(online.mean, 0.0)
            for item in data:
                online.update(item)

            self.assertIsInstance(online.mean, float)
            self.assertAlmostEqual(online.mean, case)

    @unittest.skip("currently not accurate to enough places")
    def test_online_integers_variance(self):
        """
        Test online variance computing variance on integers
        """

        # Computed using numpy
        expected = [
            5.9001890359168243, 18264.618014464173,
            0.24952741020793956, 35.203155818540431
        ]

        for data, case in zip(INTEGERS, expected):
            online = OnlineVariance()
            self.assertEqual(online.variance, 0.0)
            for item in data:
                online.update(item)

            self.assertIsInstance(online.variance, float)
            self.assertAlmostEqual(online.variance, case, places=3)

    @unittest.skip("currently not accurate to enough places")
    def test_online_float_variance(self):
        """
        Test online variance computing variance on floats.
        """

        # Computed using numpy
        expected = [
            0.073895851263651294, 766.42173756693592,
            1.0187313521468584, 348.99176719359377
        ]


        for data, case in zip(FLOATS, expected):
            online = OnlineVariance()
            self.assertEqual(online.variance, 0.0)
            for item in data:
                online.update(item)

            self.assertIsInstance(online.variance, float)
            self.assertAlmostEqual(online.variance, case, places=3)

    @unittest.skip("currently not accurate to enough places")
    def test_online_integers_standard_deviation(self):
        """
        Test online variance computing standard deviation on integers
        """

        # Computed using numpy
        expected = [
            2.4290304724142149, 135.1466537301763,
            0.49952718665548079, 5.9332247402690239
        ]

        for data, case in zip(INTEGERS, expected):
            online = OnlineVariance()
            self.assertEqual(online.standard_deviation, 0.0)
            for item in data:
                online.update(item)

            self.assertIsInstance(online.standard_deviation, float)
            self.assertAlmostEqual(online.standard_deviation, case, places=3)

    @unittest.skip("currently not accurate to enough places")
    def test_online_float_standard_deviation(self):
        """
        Test online variance computing standard deviation on floats.
        """

        # Computed using numpy
        expected = [
            0.27183791358758491, 27.684322956629007,
            1.0093222241419528, 18.681321344958278
        ]

        for data, case in zip(FLOATS, expected):
            online = OnlineVariance()
            self.assertEqual(online.standard_deviation, 0.0)
            for item in data:
                online.update(item)

            self.assertIsInstance(online.standard_deviation, float)
            self.assertAlmostEqual(online.standard_deviation, case, places=3)

    def test_online_variance_initialization(self):
        """
        Be able to initialize online variance with an iterable.
        """

        # Computed using numpy
        expected = [
            (115, 4.8260869565217392),
            (117, 219.92307692307693),
            (115, 0.47826086956521741),
            (117, -0.89743589743589747),
            (100, 0.48705447450000006),
            (100, 45.260727738500009),
            (100, -0.014150190199999982),
            (100, 99.931501583200003),
        ]

        for data, (length, mean) in zip(INTEGERS+FLOATS, expected):
            online = OnlineVariance(data)
            self.assertEqual(len(online),length)
            self.assertAlmostEqual(online.mean, mean)

    def test_online_variance_addition(self):
        """
        Be able to add two online variance objects together for a new mean.
        """

        # Computed using numpy
        expected = [
            # (mean, stddev, variance)
            (4.8260869565217392, 2.4290304724142149, 5.9001890359168243),
            (113.30172413793103, 144.15193253022923, 20779.779652199759),
            (2.652173913043478, 2.7929833769049353, 7.8007561436672956),
            (1.9396551724137931, 5.3728063576641221, 28.867048156956006),
            (2.8079323137209302, 2.8060961522546988, 7.8741756156986247),
            (23.632896622558139, 27.683598847110545, 766.38164512774028),
            (2.5748138650232555, 3.0754200874004387, 9.4582087139861208),
            (49.061163527069773, 49.150086127405451, 2415.730966331374),
            (113.30172413793103, 144.15193253022923, 20779.779652199762),
            (219.92307692307693, 135.14665373017627, 18264.618014464169),
            (111.14655172413794, 145.77129904765351, 21249.271626040427),
            (109.51282051282051, 146.08331631545036, 21340.335305719924),
            (118.80048593294931, 147.68865272870397, 21811.93814481972),
            (139.43351508686635, 133.34488923389478, 17780.859484799668),
            (118.56951604138249, 147.87525029514103, 21867.089649850604),
            (164.62742008442396, 116.55887937387467, 13585.972360893467),
            (2.652173913043478, 2.7929833769049353, 7.8007561436672956),
            (111.14655172413794, 145.77129904765351, 21249.271626040427),
            (0.47826086956521741, 0.49952718665548079, 0.24952741020793953),
            (-0.21551724137931033, 4.2837021421670043, 18.35010404280618),
            (0.48235091837209304, 0.40970422355484531, 0.16785755079867867),
            (21.307315227209301, 29.249540614746596, 855.53562617371074),
            (0.24923246967441859, 0.8170794298465649, 0.66761879467838758),
            (46.735582131720932, 51.216754643725118, 2623.1559562355387),
            (1.9396551724137931, 5.3728063576641221, 28.867048156956006),
            (109.51282051282051, 146.08331631545036, 21340.335305719924),
            (-0.21551724137931033, 4.2837021421670052, 18.350104042806187),
            (-0.89743589743589747, 5.9332247402690239, 35.203155818540431),
            (-0.25942190115207375, 4.4148407820487128, 19.490819130840489),
            (20.37360725276498, 30.025743253384654, 901.54525791817412),
            (-0.49039179271889405, 4.4321344921977124, 19.643816156928672),
            (45.567512250322572, 52.017556151674398, 2705.8261479925991),
            (2.8079323137209302, 2.8060961522546988, 7.8741756156986256),
            (118.80048593294931, 147.68865272870397, 21811.93814481972),
            (0.48235091837209304, 0.40970422355484531, 0.16785755079867867),
            (-0.25942190115207375, 4.4148407820487128, 19.490819130840489),
            (0.48705447450000006, 0.27183791358758491, 0.073895851263651294),
            (22.8738911065, 29.739170652473767, 884.41827109695691),
            (0.23645214215000002, 0.78045828247544069, 0.60911513068451473),
            (50.209278028850001, 51.447374536619328, 2646.8323467111868),
            (23.632896622558139, 27.683598847110545, 766.38164512774028),
            (139.43351508686635, 133.34488923389478, 17780.859484799668),
            (21.307315227209301, 29.2495406147466, 855.53562617371097),
            (20.373607252764977, 30.025743253384654, 901.54525791817412),
            (22.873891106500004, 29.739170652473767, 884.41827109695691),
            (45.260727738500009, 27.684322956629007, 766.4217375669358),
            (22.623288774150005, 29.936163370148371, 896.17387732421298),
            (72.59611466085002, 36.123816666776065, 1304.9301305748484),
            (2.5748138650232555, 3.0754200874004387, 9.4582087139861208),
            (118.56951604138249, 147.875250295141, 21867.089649850601),
            (0.24923246967441862, 0.8170794298465649, 0.66761879467838758),
            (-0.49039179271889405, 4.4321344921977124, 19.643816156928676),
            (0.23645214215000002, 0.78045828247544069, 0.60911513068451473),
            (22.623288774149998, 29.936163370148371, 896.17387732421298),
            (-0.014150190199999982, 1.0093222241419528, 1.0187313521468584),
            (49.958675696500002, 51.6941831967128, 2672.2885763753043),
            (49.061163527069773, 49.150086127405451, 2415.730966331374),
            (164.62742008442396, 116.55887937387467, 13585.972360893466),
            (46.735582131720932, 51.216754643725118, 2623.1559562355387),
            (45.567512250322586, 52.017556151674405, 2705.8261479925995),
            (50.209278028849994, 51.447374536619328, 2646.8323467111868),
            (72.596114660849992, 36.123816666776065, 1304.9301305748484),
            (49.958675696499995, 51.6941831967128, 2672.2885763753043),
            (99.931501583200003, 18.681321344958278, 348.99176719359377)
        ]

        for (a, b), (mean, stddev, variance) in zip(product(INTEGERS + FLOATS, repeat=2), expected):
            oa = OnlineVariance(a)
            ob = OnlineVariance(b)
            online = oa + ob

            self.assertIsNot(oa, ob)
            self.assertIsNot(oa, online)
            self.assertIsNot(ob, online)

            self.assertAlmostEqual(mean, online.mean)

            # Not precise enough for these calculations
            # self.assertAlmostEqual(stddev, online.stddev)
            # self.assertAlmostEqual(variance, online.variance)
