#!/usr/bin/env python
"""
UTM Simulator - generates test data streams for development.

Outputs ASCII floats separated by newlines, simulating the
Universal Testing Machine's load cell data stream.

Usage:
    python simulator.py --socket /tmp/utm.sock --samples 100 --rate 10 --pause 2

This creates a Unix socket server, waits for a client connection,
then streams test data: 100 samples at 10 Hz, pauses 2 seconds,
repeats indefinitely.
"""

from __future__ import print_function
import argparse
import math
import random
import time
import sys

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utm_data_logger.stream import SocketStreamServer


def generate_sine_wave(num_samples, amplitude=100.0, offset=50.0, noise=5.0):
    """
    Generate a sine wave with noise - simulates a peel test load curve.

    Args:
        num_samples: number of samples to generate
        amplitude: peak-to-peak amplitude
        offset: DC offset (base load)
        noise: random noise amplitude

    Yields:
        float values
    """
    for i in range(num_samples):
        angle = 2.0 * math.pi * i / num_samples
        value = offset + (amplitude / 2.0) * math.sin(angle)
        value += random.uniform(-noise, noise)
        yield value


def generate_random_walk(num_samples, start=50.0, step=2.0):
    """
    Generate a random walk - simulates noisy load readings.

    Args:
        num_samples: number of samples to generate
        start: starting value
        step: maximum step size

    Yields:
        float values
    """
    value = start
    for _ in range(num_samples):
        yield value
        value += random.uniform(-step, step)
        value = max(0.0, value)  # Keep non-negative


def generate_ramp(num_samples, start=0.0, end=100.0, noise=2.0):
    """
    Generate a ramp with noise - simulates tensile test loading.

    Args:
        num_samples: number of samples to generate
        start: starting value
        end: ending value
        noise: random noise amplitude

    Yields:
        float values
    """
    for i in range(num_samples):
        t = float(i) / max(1, num_samples - 1)
        value = start + t * (end - start)
        value += random.uniform(-noise, noise)
        yield value


GENERATORS = {
    'sine': generate_sine_wave,
    'walk': generate_random_walk,
    'ramp': generate_ramp,
}


def run_simulator(socket_path, samples, rate, pause, pattern, num_tests):
    """
    Run the simulator.

    Args:
        socket_path: path for Unix socket
        samples: samples per test
        rate: samples per second
        pause: pause between tests in seconds
        pattern: data pattern ('sine', 'walk', 'ramp')
        num_tests: number of tests to run (0 = infinite)
    """
    print("Starting UTM simulator")
    print("  Socket: {0}".format(socket_path))
    print("  Samples per test: {0}".format(samples))
    print("  Rate: {0} Hz".format(rate))
    print("  Pause between tests: {0}s".format(pause))
    print("  Pattern: {0}".format(pattern))
    print("  Tests: {0}".format(num_tests if num_tests > 0 else "infinite"))
    print("")

    server = SocketStreamServer(socket_path)
    print("Waiting for client connection...")

    try:
        client = server.accept()
        print("Client connected!")
        print("")

        generator = GENERATORS[pattern]
        test_count = 0
        sample_interval = 1.0 / rate

        while num_tests == 0 or test_count < num_tests:
            test_count += 1
            print("Starting test {0}...".format(test_count))

            for value in generator(samples):
                line = "{0:.6f}\n".format(value)
                client.write(line.encode('ascii'))
                time.sleep(sample_interval)

            print("  Test {0} complete ({1} samples)".format(test_count, samples))

            if num_tests == 0 or test_count < num_tests:
                print("  Pausing {0}s...".format(pause))
                time.sleep(pause)

        print("")
        print("All tests complete.")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print("Error: {0}".format(e))
    finally:
        server.close()


def main():
    parser = argparse.ArgumentParser(
        description='UTM Simulator - generates test data streams'
    )
    parser.add_argument(
        '--socket', '-s',
        default='/tmp/utm.sock',
        help='Unix socket path (default: /tmp/utm.sock)'
    )
    parser.add_argument(
        '--samples', '-n',
        type=int,
        default=100,
        help='Samples per test (default: 100)'
    )
    parser.add_argument(
        '--rate', '-r',
        type=float,
        default=10.0,
        help='Sample rate in Hz (default: 10)'
    )
    parser.add_argument(
        '--pause', '-p',
        type=float,
        default=2.0,
        help='Pause between tests in seconds (default: 2)'
    )
    parser.add_argument(
        '--pattern',
        choices=['sine', 'walk', 'ramp'],
        default='sine',
        help='Data pattern (default: sine)'
    )
    parser.add_argument(
        '--tests', '-t',
        type=int,
        default=0,
        help='Number of tests (default: 0 = infinite)'
    )

    args = parser.parse_args()

    run_simulator(
        socket_path=args.socket,
        samples=args.samples,
        rate=args.rate,
        pause=args.pause,
        pattern=args.pattern,
        num_tests=args.tests
    )


if __name__ == '__main__':
    main()
