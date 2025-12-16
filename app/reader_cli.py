#!/usr/bin/env python
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
from utm_data_logger.models import Test, TestSession


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

    print("[INFO] Starting reader (Ctrl+C to stop)")

    # Track state for output
    last_test_count = 0
    last_sample_counts = {}

    # Main loop - process events and print output
    try:
        while session.is_connected:
            session.process_events()

            # Check for new tests
            if len(session.tests) > last_test_count:
                last_test_count = len(session.tests)

            # Print new samples
            for i, test in enumerate(session.tests):
                test.update()
                test_num = i + 1
                prev_count = last_sample_counts.get(id(test), 0)

                if test.sample_count > prev_count:
                    # Print new samples
                    values, timestamps = test.snapshot
                    for j in range(prev_count, len(values)):
                        print("[SAMPLE] {:.6f} | Test {} | {}".format(
                            timestamps[j], test_num, values[j]
                        ))
                    last_sample_counts[id(test)] = test.sample_count
                    sys.stdout.flush()

                # Check for test completion
                if test.status != Test.STATUS_IN_PROGRESS and prev_count > 0:
                    if id(test) in last_sample_counts:
                        status = "ERROR" if test.status == Test.STATUS_ERROR else "COMPLETE"
                        print("[TEST_{}] Test {} | {} samples".format(
                            status, test_num, test.sample_count
                        ))
                        del last_sample_counts[id(test)]
                        sys.stdout.flush()

            # Check for disconnect
            if session.disconnect_reason:
                print("[DISCONNECT] {}".format(session.disconnect_reason))
                break

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted")

    # Clean up
    print("[INFO] Stopping")
    session.disconnect()

    # Summary
    print("[INFO] Total tests: {}".format(len(session.tests)))
    for i, test in enumerate(session.tests, 1):
        test.update()
        status = "ERROR" if test.status == Test.STATUS_ERROR else "OK"
        print("  Test {}: {} samples [{}]".format(i, test.sample_count, status))


if __name__ == '__main__':
    main()
