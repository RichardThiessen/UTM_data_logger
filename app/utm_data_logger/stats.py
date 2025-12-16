"""
Statistics utilities for UTM data logger.
Linear regression for rate estimation, standard deviation.
"""

import logging
import math

logger = logging.getLogger(__name__)


def linear_regression(x_values, y_values):
    """
    Simple linear regression: y = slope * x + intercept

    Args:
        x_values: list of x coordinates (e.g., sample indices)
        y_values: list of y coordinates (e.g., timestamps)

    Returns:
        (slope, intercept) tuple

    Raises:
        ValueError: if lists are empty or different lengths
    """
    n = len(x_values)
    if n == 0:
        raise ValueError("Cannot perform regression on empty data")
    if n != len(y_values):
        raise ValueError("x_values and y_values must have same length")
    if n == 1:
        # Single point - can't determine slope, return 0 slope
        return (0.0, y_values[0])

    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_xx = sum(x * x for x in x_values)

    # slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x^2)
    denominator = n * sum_xx - sum_x * sum_x
    if denominator == 0:
        # All x values are the same - can't determine slope
        return (0.0, sum_y / n)

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    return (slope, intercept)


def estimate_sample_rate(timestamps):
    """
    Estimate the sample rate from timestamps using linear regression.

    Args:
        timestamps: list of timestamps (seconds since epoch)

    Returns:
        Estimated samples per second, or None if not enough data
    """
    n = len(timestamps)
    if n < 2:
        return None

    # x = sample index (0, 1, 2, ...), y = timestamp
    # slope = seconds per sample, so rate = 1/slope
    indices = list(range(n))
    slope, _ = linear_regression(indices, timestamps)

    if slope <= 0:
        logger.debug("estimate_sample_rate: n=%d, slope=%.6f (invalid)", n, slope)
        return None

    rate = 1.0 / slope
    logger.debug("estimate_sample_rate: n=%d, slope=%.6f, rate=%.2f Hz", n, slope, rate)
    return rate


def estimate_duration(num_samples, sample_rate):
    """
    Estimate test duration from sample count and rate.

    Args:
        num_samples: number of samples in test
        sample_rate: samples per second

    Returns:
        Estimated duration in seconds, or None if rate unknown
    """
    if sample_rate is None or sample_rate <= 0:
        return None
    duration = num_samples / sample_rate
    logger.debug("estimate_duration: n=%d, rate=%.2f Hz, duration=%.3f s",
                 num_samples, sample_rate, duration)
    return duration


def stdev(values):
    """
    Calculate population standard deviation.

    Args:
        values: list of numeric values

    Returns:
        Standard deviation, or None if fewer than 2 values
    """
    n = len(values)
    if n < 2:
        return None

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    return math.sqrt(variance)
