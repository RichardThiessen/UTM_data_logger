# SPDX-License-Identifier: MIT
"""Tests for reader module."""

import unittest
import threading
import time
import sys
import os

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utm_data_logger.reader import StreamReader
from utm_data_logger.stream import StreamDisconnected


class MockStream(object):
    """Mock byte stream for testing."""

    def __init__(self, chunks=None):
        """
        Args:
            chunks: list of (data, delay) tuples, or None for data to be added later
        """
        self._chunks = chunks if chunks else []
        self._index = 0
        self._timeout = None
        self._closed = False
        self._lock = threading.Lock()
        self._data_event = threading.Event()

    def add_chunk(self, data, delay=0):
        """Add a chunk of data to be read."""
        with self._lock:
            self._chunks.append((data, delay))
        self._data_event.set()

    def close_stream(self):
        """Signal end of stream (raises StreamDisconnected on next read)."""
        self._closed = True
        self._data_event.set()

    def read(self, size):
        while True:
            with self._lock:
                if self._index < len(self._chunks):
                    data, delay = self._chunks[self._index]
                    self._index += 1
                    if delay > 0:
                        time.sleep(delay)
                    return data.encode('ascii') if isinstance(data, str) else data
                if self._closed:
                    raise StreamDisconnected("Mock stream closed")

            # Wait for more data or timeout
            if self._timeout is not None and self._timeout > 0:
                if not self._data_event.wait(self._timeout):
                    # Timeout - return empty bytes
                    return b''
                self._data_event.clear()
            else:
                self._data_event.wait()
                self._data_event.clear()

    def close(self):
        self._closed = True
        self._data_event.set()

    def set_timeout(self, timeout):
        self._timeout = timeout


def drain_queue(q):
    """Drain all events from queue and return as list."""
    events = []
    while True:
        try:
            events.append(q.get_nowait())
        except Empty:
            break
    return events


class TestStreamReader(unittest.TestCase):

    def test_sample_events(self):
        """Test that reader pushes sample events to queue."""
        stream = MockStream([
            ("1.0\n2.0\n3.0\n", 0),
        ])
        queue = Queue()

        reader = StreamReader(stream, queue)
        reader.start()

        time.sleep(0.1)
        stream.close_stream()
        reader.stop()

        events = drain_queue(queue)

        # Should have 3 sample events + complete + disconnect
        sample_events = [e for e in events if e[0] == 'sample']
        self.assertEqual(len(sample_events), 3)
        self.assertEqual(sample_events[0][1], 1.0)
        self.assertEqual(sample_events[1][1], 2.0)
        self.assertEqual(sample_events[2][1], 3.0)

    def test_complete_event_on_disconnect(self):
        """Test that disconnect triggers complete event."""
        stream = MockStream([
            ("1.0\n2.0\n", 0),
        ])
        queue = Queue()

        reader = StreamReader(stream, queue)
        reader.start()

        time.sleep(0.1)
        stream.close_stream()
        reader.stop()

        events = drain_queue(queue)

        # Should have complete event before disconnect
        event_types = [e[0] for e in events]
        self.assertIn('complete', event_types)
        self.assertIn('disconnect', event_types)
        # Complete should come before disconnect
        self.assertLess(event_types.index('complete'),
                       event_types.index('disconnect'))

    def test_complete_event_on_timeout(self):
        """Test that timeout triggers complete event."""
        import socket as sock_module
        import tempfile

        socket_path = tempfile.mktemp(suffix='.sock')

        server = sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM)
        try:
            os.unlink(socket_path)
        except OSError:
            pass
        server.bind(socket_path)
        server.listen(1)

        queue = Queue()

        def connect_and_read():
            from utm_data_logger.stream import SocketStream
            stream = SocketStream(socket_path)
            reader = StreamReader(stream, queue, min_timeout=0.05, max_timeout=0.15)
            reader.start()
            return reader, stream

        reader_result = [None, None]
        def client_thread():
            r, s = connect_and_read()
            reader_result[0] = r
            reader_result[1] = s

        client = threading.Thread(target=client_thread)
        client.start()
        conn, _ = server.accept()
        client.join()
        reader = reader_result[0]
        stream = reader_result[1]

        # Send first test
        conn.sendall(b"1.0\n2.0\n")
        time.sleep(0.3)  # Wait for timeout

        events = drain_queue(queue)
        complete_count = sum(1 for e in events if e[0] == 'complete')
        self.assertEqual(complete_count, 1)

        # Send second test
        conn.sendall(b"3.0\n4.0\n")
        time.sleep(0.3)

        events = drain_queue(queue)
        complete_count = sum(1 for e in events if e[0] == 'complete')
        self.assertEqual(complete_count, 1)

        # Clean up
        conn.close()
        reader.stop()
        stream.close()
        server.close()
        try:
            os.unlink(socket_path)
        except OSError:
            pass

    def test_error_event_on_invalid_float(self):
        """Test that invalid data triggers error event."""
        stream = MockStream([
            ("1.0\ngarbage\n", 0),
        ])
        queue = Queue()

        reader = StreamReader(stream, queue)
        reader.start()

        time.sleep(0.1)
        stream.close_stream()
        reader.stop()

        events = drain_queue(queue)
        error_events = [e for e in events if e[0] == 'error']
        self.assertEqual(len(error_events), 1)
        self.assertIn('garbage', error_events[0][1])

    def test_partial_line_buffering(self):
        """Test that partial lines are buffered correctly."""
        stream = MockStream([
            ("1.0\n2.", 0),  # partial
            ("5\n3.0\n", 0),  # completes 2.5
        ])
        queue = Queue()

        reader = StreamReader(stream, queue)
        reader.start()

        time.sleep(0.1)
        stream.close_stream()
        reader.stop()

        events = drain_queue(queue)
        sample_events = [e for e in events if e[0] == 'sample']
        values = [e[1] for e in sample_events]
        self.assertEqual(values, [1.0, 2.5, 3.0])

    def test_windows_line_endings(self):
        """Test that reader handles Windows CRLF line endings."""
        stream = MockStream([
            ("1.0\r\n2.0\r\n3.0\r\n", 0),
        ])
        queue = Queue()

        reader = StreamReader(stream, queue)
        reader.start()

        time.sleep(0.1)
        stream.close_stream()
        reader.stop()

        events = drain_queue(queue)
        sample_events = [e for e in events if e[0] == 'sample']
        values = [e[1] for e in sample_events]
        self.assertEqual(values, [1.0, 2.0, 3.0])

    def test_unterminated_line_at_disconnect(self):
        """Test that reader handles final value without trailing newline."""
        stream = MockStream([
            ("1.0\n2.0\n3.0", 0),  # No trailing newline on last value
        ])
        queue = Queue()

        reader = StreamReader(stream, queue)
        reader.start()

        time.sleep(0.1)
        stream.close_stream()
        reader.stop()

        events = drain_queue(queue)
        sample_events = [e for e in events if e[0] == 'sample']
        values = [e[1] for e in sample_events]
        self.assertEqual(values, [1.0, 2.0, 3.0])

    def test_disconnect_event(self):
        """Test that disconnect event is pushed."""
        stream = MockStream([
            ("1.0\n", 0),
        ])
        queue = Queue()

        reader = StreamReader(stream, queue)
        reader.start()

        time.sleep(0.1)
        stream.close_stream()
        reader.stop()

        events = drain_queue(queue)
        disconnect_events = [e for e in events if e[0] == 'disconnect']
        self.assertEqual(len(disconnect_events), 1)
        self.assertIn('Mock stream closed', disconnect_events[0][1])


class TestIntegrationWithSocket(unittest.TestCase):
    """Integration test using actual Unix sockets."""

    def test_socket_communication(self):
        """Test end-to-end with real socket."""
        import socket as sock_module
        import tempfile

        socket_path = tempfile.mktemp(suffix='.sock')

        # Create server
        server = sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM)
        try:
            os.unlink(socket_path)
        except OSError:
            pass
        server.bind(socket_path)
        server.listen(1)

        queue = Queue()

        def connect_and_read():
            from utm_data_logger.stream import SocketStream
            stream = SocketStream(socket_path)
            reader = StreamReader(stream, queue, max_timeout=0.2)
            reader.start()
            return reader, stream

        # Connect client in thread
        reader_result = [None, None]
        def client_thread():
            r, s = connect_and_read()
            reader_result[0] = r
            reader_result[1] = s

        client = threading.Thread(target=client_thread)
        client.start()

        # Accept connection
        conn, _ = server.accept()

        # Wait for client to connect
        client.join()
        reader = reader_result[0]
        stream = reader_result[1]

        # Send test data
        conn.sendall(b"10.0\n20.0\n30.0\n")
        time.sleep(0.1)

        # Wait for timeout to complete test
        time.sleep(0.3)

        # Clean up
        conn.close()
        reader.stop()
        stream.close()
        server.close()
        try:
            os.unlink(socket_path)
        except OSError:
            pass

        events = drain_queue(queue)
        sample_events = [e for e in events if e[0] == 'sample']
        values = [e[1] for e in sample_events]
        self.assertEqual(values, [10.0, 20.0, 30.0])

        complete_events = [e for e in events if e[0] == 'complete']
        self.assertEqual(len(complete_events), 1)


if __name__ == '__main__':
    unittest.main()
