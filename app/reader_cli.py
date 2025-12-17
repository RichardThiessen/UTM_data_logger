#!/usr/bin/env python
# SPDX-License-Identifier: MIT
"""
CLI client for StreamReader - test reader functionality without UI.

Usage:
    python reader_cli.py --serial /dev/ttyACM0 --baudrate 9600
    python reader_cli.py --socket /tmp/utm.sock
    python reader_cli.py --socket /tmp/utm.sock --debug reader,stream
"""

from __future__ import print_function
import argparse
import sys
import time

from utm_data_logger.log import setup_logging
from utm_data_logger.models import TestSession


def main():
    parser = argparse.ArgumentParser(
        description='CLI client for StreamReader - test without UI'
    )

    # Connection options (mutually exclusive)
    conn_group = parser.add_mutually_exclusive_group(required=True)
    conn_group.add_argument(
        '--serial', '-p',
        metavar='PORT',
        help='Serial port path (e.g., /dev/ttyACM0, COM1)'
    )
    conn_group.add_argument(
        '--socket', '-s',
        metavar='PATH',
        help='Unix socket path'
    )

    # Serial options
    parser.add_argument(
        '--baudrate', '-b',
        type=int,
        default=9600,
        help='Baudrate for serial connection (default: 9600)'
    )

    # Debug options
    parser.add_argument(
        '--debug', '-d',
        metavar='MODULES',
        help='Enable debug logging for modules (comma-separated: reader,stream,models,stats,all)'
    )

    args = parser.parse_args()

    setup_logging(args.debug)

    # Create session
    session = TestSession()

    # Connect
    try:
        if args.serial:
            print("[CONNECTING] Serial {} @ {}".format(args.serial, args.baudrate))
            session.connect(serial=(args.serial, args.baudrate))
            print("[CONNECTED] Serial {} @ {}".format(args.serial, args.baudrate))
        else:
            print("[CONNECTING] Socket {}".format(args.socket))
            session.connect(socket=args.socket)
            print("[CONNECTED] Socket {}".format(args.socket))
    except Exception as e:
        print("[ERROR] Failed to connect: {}".format(e))
        sys.exit(1)

    print("[INFO] Waiting for data (Ctrl+C to stop)")

    # Track current test index and sample count
    current_test_idx = 0
    last_sample_count = 0

    # Main loop
    try:
        while session.is_connected:
            session.process_events()

            # Check for disconnect
            if session.disconnect_reason:
                print("[DISCONNECT] {}".format(session.disconnect_reason))
                break

            # If current test doesn't exist yet, nothing to do
            if current_test_idx >= len(session.tests):
                time.sleep(0.01)
                continue

            test = session.tests[current_test_idx]
            test_num = current_test_idx + 1

            # Print new samples (use len(values) not sample_count - that's only updated on completion)
            current_count = len(test.values)
            if current_count > last_sample_count:
                for i in range(last_sample_count, current_count):
                    print("[SAMPLE] Test {} | idx={} t={:.6f} v={:.6f}".format(
                        test_num, i, test.timestamps[i], test.values[i]
                    ))
                last_sample_count = current_count
                sys.stdout.flush()

            # Check if test completed - print summary and move to next
            if test.status != test.STATUS_IN_PROGRESS:
                status = "ERROR" if test.status == test.STATUS_ERROR else "COMPLETE"
                print("[TEST_{}] Test {} | samples={} min={:.4f} max={:.4f} mean={:.4f} rate={:.1f}Hz duration={:.2f}s".format(
                    status, test_num,
                    test.sample_count,
                    test.min_value or 0,
                    test.max_value or 0,
                    test.mean_value or 0,
                    test.estimated_rate or 0,
                    test.estimated_duration or 0
                ))
                sys.stdout.flush()
                current_test_idx += 1
                last_sample_count = 0

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted")

    # Clean up
    session.disconnect()
    print("[INFO] Done. Total tests: {}".format(len(session.tests)))


if __name__ == '__main__':
    main()
