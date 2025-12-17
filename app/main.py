#!/usr/bin/env python
# SPDX-License-Identifier: MIT
"""
UTM Data Logger - Main entry point.

Usage:
    python main.py                    # Normal mode - connect to serial port
    python main.py --socket PATH      # Development mode - connect to Unix socket
    python main.py --debug reader,ui  # Enable debug logging for modules
"""

import argparse

from utm_data_logger.log import setup_logging
from utm_data_logger.models import TestSession
from utm_data_logger.ui import run_app


def main():
    parser = argparse.ArgumentParser(description='UTM Data Logger')
    parser.add_argument(
        '--socket', '-s',
        help='Connect to Unix socket instead of serial port (development mode)'
    )
    parser.add_argument(
        '--debug', '-d',
        metavar='MODULES',
        help='Enable debug logging for modules (comma-separated: reader,ui,graph,stats,models,stream,all)'
    )
    args = parser.parse_args()

    setup_logging(args.debug)

    session = TestSession()
    app = run_app(session, socket_path=args.socket)

    try:
        app.mainloop()
    finally:
        app.shutdown()


if __name__ == '__main__':
    main()
