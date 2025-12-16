"""Tests for stats module."""

import unittest
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utm_data_logger.stats import (
    linear_regression,
    estimate_sample_rate,
    estimate_duration,
    stdev,
)


class TestLinearRegression(unittest.TestCase):

    def test_perfect_line(self):
        # y = 2x + 1
        x = [0, 1, 2, 3, 4]
        y = [1, 3, 5, 7, 9]
        slope, intercept = linear_regression(x, y)
        self.assertAlmostEqual(slope, 2.0)
        self.assertAlmostEqual(intercept, 1.0)

    def test_horizontal_line(self):
        # y = 5
        x = [0, 1, 2, 3]
        y = [5, 5, 5, 5]
        slope, intercept = linear_regression(x, y)
        self.assertAlmostEqual(slope, 0.0)
        self.assertAlmostEqual(intercept, 5.0)

    def test_single_point(self):
        x = [3]
        y = [7]
        slope, intercept = linear_regression(x, y)
        self.assertEqual(slope, 0.0)
        self.assertEqual(intercept, 7.0)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            linear_regression([], [])

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            linear_regression([1, 2], [1])


class TestEstimateSampleRate(unittest.TestCase):

    def test_constant_rate(self):
        # 10 samples at 10 Hz = 0.1s intervals
        timestamps = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        rate = estimate_sample_rate(timestamps)
        self.assertAlmostEqual(rate, 10.0, places=1)

    def test_different_rate(self):
        # 5 samples at 2 Hz = 0.5s intervals
        timestamps = [0.0, 0.5, 1.0, 1.5, 2.0]
        rate = estimate_sample_rate(timestamps)
        self.assertAlmostEqual(rate, 2.0, places=1)

    def test_single_sample_returns_none(self):
        rate = estimate_sample_rate([1.0])
        self.assertIsNone(rate)

    def test_empty_returns_none(self):
        rate = estimate_sample_rate([])
        self.assertIsNone(rate)


class TestEstimateDuration(unittest.TestCase):

    def test_basic(self):
        # 100 samples at 10 Hz = 10 seconds
        duration = estimate_duration(100, 10.0)
        self.assertAlmostEqual(duration, 10.0)

    def test_none_rate(self):
        duration = estimate_duration(100, None)
        self.assertIsNone(duration)

    def test_zero_rate(self):
        duration = estimate_duration(100, 0)
        self.assertIsNone(duration)


class TestStdev(unittest.TestCase):

    def test_basic(self):
        # stdev of [2, 4, 4, 4, 5, 5, 7, 9] = 2.0
        values = [2, 4, 4, 4, 5, 5, 7, 9]
        result = stdev(values)
        self.assertAlmostEqual(result, 2.0)

    def test_constant_values(self):
        values = [5, 5, 5, 5]
        result = stdev(values)
        self.assertAlmostEqual(result, 0.0)

    def test_single_value_returns_none(self):
        result = stdev([5])
        self.assertIsNone(result)

    def test_empty_returns_none(self):
        result = stdev([])
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
