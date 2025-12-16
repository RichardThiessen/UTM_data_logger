"""
Logging configuration for UTM data logger.
"""

import logging
import sys

# Module shortnames mapping
MODULE_MAP = {
    'reader': 'utm_data_logger.reader',
    'ui': 'utm_data_logger.ui',
    'graph': 'utm_data_logger.graph',
    'stats': 'utm_data_logger.stats',
    'models': 'utm_data_logger.models',
    'stream': 'utm_data_logger.stream',
    'all': 'utm_data_logger',
}


def setup_logging(debug_modules=None):
    """
    Configure logging based on debug module list.

    Args:
        debug_modules: comma-separated string of module shortnames,
                       or None for default (warnings only)
    """
    # Default format
    fmt = '[%(name)s] %(message)s'
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))

    # Set root utm_data_logger logger to WARNING by default
    root_logger = logging.getLogger('utm_data_logger')
    root_logger.setLevel(logging.WARNING)
    root_logger.addHandler(handler)

    if not debug_modules:
        return

    # Parse and enable debug for specified modules
    for name in debug_modules.split(','):
        name = name.strip()
        if not name:
            continue

        module_name = MODULE_MAP.get(name, name)
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.DEBUG)
