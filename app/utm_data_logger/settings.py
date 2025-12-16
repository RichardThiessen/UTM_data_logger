"""
Settings persistence for UTM data logger.
Stores COM port, baudrate, and other configuration in INI file.
"""

import os

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


# Default settings
DEFAULTS = {
    'port': '',
    'baudrate': '9600',
    'auto_reconnect': True,
    'export_columns': 'mean,peak,low,stdev',
    'export_datapoints': False,
    'export_transpose': False,
    'export_headers': True,
}

# Available export columns (user-visible names -> internal attribute names)
EXPORT_COLUMNS = {
    'test': 'test',       # Test number
    'mean': 'mean_value',
    'peak': 'max_value',
    'low': 'min_value',
    'stdev': 'stdev',
    'points': 'sample_count',
}

# Common baudrates for serial devices
BAUDRATES = [
    '300', '1200', '2400', '4800', '9600', '19200',
    '38400', '57600', '115200'
]


def _get_settings_path():
    """Get path to settings file in app directory."""
    # Settings file lives next to the package
    package_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(package_dir)
    return os.path.join(app_dir, 'settings.ini')


def load_settings():
    """
    Load settings from INI file.

    Returns:
        dict with 'port' and 'baudrate' keys
    """
    settings = dict(DEFAULTS)
    path = _get_settings_path()

    if os.path.exists(path):
        config = configparser.ConfigParser()
        try:
            config.read(path)
            if config.has_section('serial'):
                if config.has_option('serial', 'port'):
                    settings['port'] = config.get('serial', 'port')
                if config.has_option('serial', 'baudrate'):
                    settings['baudrate'] = config.get('serial', 'baudrate')
                if config.has_option('serial', 'auto_reconnect'):
                    settings['auto_reconnect'] = config.getboolean('serial', 'auto_reconnect')
            if config.has_section('export'):
                if config.has_option('export', 'columns'):
                    settings['export_columns'] = config.get('export', 'columns')
                if config.has_option('export', 'datapoints'):
                    settings['export_datapoints'] = config.getboolean('export', 'datapoints')
                if config.has_option('export', 'transpose'):
                    settings['export_transpose'] = config.getboolean('export', 'transpose')
                if config.has_option('export', 'headers'):
                    settings['export_headers'] = config.getboolean('export', 'headers')
        except Exception:
            pass  # Use defaults on any error

    return settings


def save_settings(settings):
    """
    Save settings to INI file.

    Args:
        settings: dict with 'port' and 'baudrate' keys
    """
    path = _get_settings_path()

    config = configparser.ConfigParser()
    config.add_section('serial')
    config.set('serial', 'port', settings.get('port', ''))
    config.set('serial', 'baudrate', settings.get('baudrate', '9600'))
    config.set('serial', 'auto_reconnect', str(settings.get('auto_reconnect', True)))
    config.add_section('export')
    config.set('export', 'columns', settings.get('export_columns', 'mean,peak,low,stdev'))
    config.set('export', 'datapoints', str(settings.get('export_datapoints', False)))
    config.set('export', 'transpose', str(settings.get('export_transpose', False)))
    config.set('export', 'headers', str(settings.get('export_headers', True)))

    try:
        with open(path, 'w') as f:
            config.write(f)
    except Exception:
        pass  # Silently fail if we can't write


def list_serial_ports():
    """
    List available serial ports.

    Returns:
        list of port names (e.g., ['COM1', 'COM3'] on Windows,
        ['/dev/ttyUSB0', '/dev/ttyACM0'] on Linux)
    """
    ports = []

    # Try pyserial's list_ports if available
    try:
        import serial.tools.list_ports
        for port_info in serial.tools.list_ports.comports():
            ports.append(port_info.device)
        return sorted(ports)
    except ImportError:
        pass

    # Fallback: try common port names
    import sys
    if sys.platform.startswith('win'):
        # Windows: try COM1-COM20
        import serial
        for i in range(1, 21):
            port = 'COM{}'.format(i)
            try:
                s = serial.Serial(port)
                s.close()
                ports.append(port)
            except (OSError, serial.SerialException):
                pass
    else:
        # Linux/Mac: look for tty devices
        import glob
        ports.extend(glob.glob('/dev/ttyUSB*'))
        ports.extend(glob.glob('/dev/ttyACM*'))
        ports.extend(glob.glob('/dev/tty.usbserial*'))
        ports.extend(glob.glob('/dev/tty.usbmodem*'))

    return sorted(ports)
