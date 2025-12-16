"""
Data models for UTM data logger.

Test: Single object holding sample data and cached stats.
TestSession: Manages connection, event queue, and test lifecycle.
"""

import logging

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

from . import stats

logger = logging.getLogger(__name__)


class Test(object):
    """
    Test object holding sample data and cached statistics.

    Samples are appended via add_sample().
    Call update() to refresh cached stats from current data.
    """

    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETE = 'complete'
    STATUS_ERROR = 'error'

    def __init__(self):
        # Raw sample data
        self.values = []
        self.timestamps = []

        # Test status
        self.status = self.STATUS_IN_PROGRESS
        self.error_message = None

        # Cached stats (updated by update())
        self.sample_count = 0
        self.min_value = None
        self.max_value = None
        self.mean_value = None
        self.stdev = None
        self.estimated_rate = None
        self.estimated_duration = None

    def add_sample(self, value, timestamp):
        """Add a sample and update snapshot."""
        self.values.append(value)
        self.timestamps.append(timestamp)

    def update(self):
        """
        recalculate statistics.
        """
        values, timestamps = self.values,self.timestamps

        self.sample_count = len(values)
        self.min_value = min(values) if values else None
        self.max_value = max(values) if values else None
        self.mean_value = sum(values) / len(values) if values else None
        self.stdev = stats.stdev(values)
        self.estimated_rate = stats.estimate_sample_rate(timestamps)
        self.estimated_duration = stats.estimate_duration(len(values), self.estimated_rate)


class TestSession(object):
    """
    Manages connection, event queue, and test lifecycle.

    Reader thread pushes events to queue.
    UI calls process_events() to update state, then reads tests.
    """

    def __init__(self):
        # Event queue for reader -> session communication
        self.queue = Queue()

        # Connection state
        self._stream = None
        self._reader = None
        self.disconnect_reason = None

        # Test state
        self.tests = []  # UI can read/modify this list
        self._active_test = None  # Internal write target

    @property
    def is_connected(self):
        """Check if connected and reader is running."""
        return self._reader is not None and self._reader.is_running()

    def connect(self, serial=None, socket=None):
        """
        Connect to data source.

        Args:
            serial: tuple of (port, baudrate) for serial connection
            socket: path string for Unix socket connection
        """
        from .stream import SerialStream, SocketStream
        from .reader import StreamReader

        self.disconnect()

        try:
            if serial:
                port, baudrate = serial
                logger.debug("connecting to serial: %s @ %s", port, baudrate)
                self._stream = SerialStream(port, baudrate)
            elif socket:
                logger.debug("connecting to socket: %s", socket)
                self._stream = SocketStream(socket)
            else:
                return

            self._reader = StreamReader(self._stream, self.queue)
            self._reader.start()
            self.disconnect_reason = None
            logger.debug("connected")

        except Exception as e:
            logger.debug("connect failed: %s", e)
            self.disconnect_reason = str(e)
            self._stream = None
            self._reader = None

    def disconnect(self):
        """Disconnect from data source."""
        if self._reader:
            self._reader.stop()
            self._reader = None
        if self._stream:
            self._stream.close()
            self._stream = None

    def process_events(self):
        """
        Drain event queue and update state.

        Call this from UI update loop.
        """
        test_dirty=False
        while True:
            try:
                event = self.queue.get_nowait()
            except Empty:
                break

            event_type = event[0]

            if event_type == 'sample':
                _, value, timestamp = event
                if self._active_test is None:
                    self._active_test = Test()
                    self.tests.append(self._active_test)
                    test_dirty=True
                    logger.debug("started test #%d", len(self.tests))
                self._active_test.add_sample(value, timestamp)

            elif event_type == 'complete':
                if self._active_test is not None:
                    self._active_test.status = Test.STATUS_COMPLETE
                    logger.debug("completed test, n=%d", len(self._active_test.values))
                    if test_dirty:self._active_test.update() #update dirty active test before it vecomes inactive
                    self._active_test = None

            elif event_type == 'error':
                _, message = event
                if self._active_test is not None:
                    self._active_test.status = Test.STATUS_ERROR
                    self._active_test.error_message = message
                    logger.debug("error test: %s", message)
                    if test_dirty:self._active_test.update() #update dirty active test before it vecomes inactive
                    self._active_test = None

            elif event_type == 'disconnect':
                _, reason = event
                self.disconnect_reason = reason
                logger.debug("disconnect: %s", reason)
                # Complete any in-progress test
                if self._active_test is not None:
                    self._active_test.status = Test.STATUS_COMPLETE
                    if test_dirty:self._active_test.update() #update dirty active test before it vecomes inactive
                    self._active_test = None
        if test_dirty and self._active_test:
            self._active_test.update()

    def delete_test(self, test):
        """Remove a test from the list."""
        if test in self.tests:
            self.tests.remove(test)
        # Note: if test is _active_test, samples still go there
        # but UI won't see it (test is no longer in tests list)

    def clear_all(self):
        """Remove all tests from the list."""
        self.tests = []
        # Note: _active_test keeps receiving samples if in progress
