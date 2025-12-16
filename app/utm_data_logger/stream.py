"""
Byte stream abstractions for UTM data logger.
Provides unified interface for sockets and serial ports.
"""

import socket


class StreamDisconnected(Exception):
    """Raised when a stream is disconnected or reaches EOF."""

    def __init__(self, reason=None):
        self.reason = reason or "Stream disconnected"
        super(StreamDisconnected, self).__init__(self.reason)


class ByteStream(object):
    """
    Abstract base class for byte streams.
    Subclasses must implement read(), close(), and set_timeout().
    """

    def read(self, size):
        """
        Read up to size bytes from the stream.
        Blocks until data is available or timeout expires.
        Returns bytes, or b'' if timeout with no data.
        Raises StreamDisconnected on disconnect or EOF.
        """
        raise NotImplementedError()

    def close(self):
        """Close the stream."""
        raise NotImplementedError()

    def set_timeout(self, timeout):
        """
        Set read timeout in seconds.
        None means block forever.
        """
        raise NotImplementedError()


class SocketStream(ByteStream):
    """
    ByteStream implementation for Unix sockets.
    Connects to an existing socket server.
    """

    def __init__(self, socket_path):
        """
        Create a socket stream connected to the given path.

        Args:
            socket_path: path to Unix domain socket
        """
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.connect(socket_path)

    def read(self, size):
        """Read up to size bytes from the socket."""
        try:
            data = self._socket.recv(size)
        except socket.timeout:
            return b''
        except socket.error as e:
            raise StreamDisconnected("Socket error: {}".format(e))
        if not data:
            raise StreamDisconnected("Connection closed")
        return data

    def close(self):
        """Close the socket."""
        self._socket.close()

    def set_timeout(self, timeout):
        """Set socket timeout."""
        self._socket.settimeout(timeout)


class SocketStreamServer(object):
    """
    Helper to create a Unix socket server that accepts one connection.
    Useful for testing - simulator creates server, app connects.
    """

    def __init__(self, socket_path):
        """
        Create and bind a socket server.

        Args:
            socket_path: path to create Unix domain socket
        """
        self._socket_path = socket_path
        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Remove existing socket file if present
        try:
            import os
            os.unlink(socket_path)
        except OSError:
            pass
        self._server_socket.bind(socket_path)
        self._server_socket.listen(1)
        self._client_socket = None

    def accept(self):
        """
        Wait for a client connection.
        Returns a ByteStream for communicating with the client.
        """
        self._client_socket, _ = self._server_socket.accept()
        return _ConnectedSocketStream(self._client_socket)

    def close(self):
        """Close the server socket."""
        if self._client_socket:
            self._client_socket.close()
        self._server_socket.close()
        try:
            import os
            os.unlink(self._socket_path)
        except OSError:
            pass


class _ConnectedSocketStream(ByteStream):
    """ByteStream wrapper for an already-connected socket."""

    def __init__(self, sock):
        self._socket = sock

    def read(self, size):
        try:
            data = self._socket.recv(size)
        except socket.timeout:
            return b''
        except socket.error as e:
            raise StreamDisconnected("Socket error: {}".format(e))
        if not data:
            raise StreamDisconnected("Connection closed")
        return data

    def write(self, data):
        """Write data to the socket."""
        self._socket.sendall(data)

    def close(self):
        self._socket.close()

    def set_timeout(self, timeout):
        self._socket.settimeout(timeout)


class SerialStream(ByteStream):
    """
    ByteStream implementation for serial ports.
    Wraps pyserial.
    """

    def __init__(self, port, baudrate=9600):
        """
        Create a serial stream.

        Args:
            port: serial port name (e.g., 'COM1', '/dev/ttyUSB0')
            baudrate: baud rate (default 9600)
        """
        import serial
        self._serial_module = serial
        self._serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=None  # Blocking by default
        )

    def read(self, size):
        """Read up to size bytes from serial port."""
        try:
            # Block for at least 1 byte, then grab everything available up to size
            data = self._serial.read(1)
            if data:
                waiting = self._serial.in_waiting
                extra = min(waiting, size - 1)
                if extra > 0:
                    data += self._serial.read(extra)
            return data
        except self._serial_module.SerialException as e:
            raise StreamDisconnected("Serial error: {}".format(e))

    def close(self):
        """Close the serial port."""
        self._serial.close()

    def set_timeout(self, timeout):
        """Set read timeout in seconds."""
        self._serial.timeout = timeout
