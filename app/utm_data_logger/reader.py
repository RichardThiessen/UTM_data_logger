"""
Stream reader for UTM data logger.
Reads ASCII float data, detects test boundaries via adaptive timeout.
Pushes events to queue for processing by TestSession.
"""

import logging
import threading
import time

from .stream import StreamDisconnected

logger = logging.getLogger(__name__)

clamp = lambda val, low, high:max(low,min(high,val)) 

class StreamReader(object):
    """
    Reads load cell data from a byte stream, parses ASCII floats,
    and manages test boundaries using adaptive timeout detection.

    Runs in a dedicated thread. Pushes events to queue:
    - ('sample', value, timestamp)
    - ('complete',)
    - ('error', message)
    - ('disconnect', reason)
    """

    # Timeout bounds in seconds
    DEFAULT_MIN_TIMEOUT = 0.1
    DEFAULT_MAX_TIMEOUT = 1.0
    TIMEOUT_MULTIPLIER = 5.0

    # Read buffer size
    READ_SIZE = 1024

    def __init__(self, stream, queue, min_timeout=None, max_timeout=None):
        """
        Create a stream reader.

        Args:
            stream: ByteStream to read from
            queue: Queue to push events to
            min_timeout: minimum adaptive timeout (default 0.1s)
            max_timeout: maximum adaptive timeout (default 1.0s)
        """
        self._stream = stream
        self._queue = queue
        self._min_timeout = min_timeout if min_timeout is not None else self.DEFAULT_MIN_TIMEOUT
        self._max_timeout = max_timeout if max_timeout is not None else self.DEFAULT_MAX_TIMEOUT

        self._thread = None
        self._stop_event = threading.Event()
        self.reset()
    
    def reset(self):
        self._buffer = ""
        self._sample_count = 0
        self._last_sample_time = 0
        self._max_gap_this_test = 0

    def start(self):
        """Start the reader thread."""
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def stop(self, timeout=2.0):
        """
        Stop the reader thread.

        Args:
            timeout: seconds to wait for thread to finish
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def is_running(self):
        """Check if reader thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def _get_current_timeout(self):
        """Calculate adaptive timeout based on observed gaps."""
        if self._sample_count<2:return self._max_timeout
        timeout = self._max_gap_this_test * self.TIMEOUT_MULTIPLIER
        return max(self._min_timeout, min(self._max_timeout, timeout))
    
    def _run(self):
        """Main reader loop."""
        self._stream.set_timeout(self._min_timeout)
        try:
            while not self._stop_event.is_set():
                timeout = self._get_current_timeout()
                #self._stream.set_timeout(timeout)
                # repeatedly changing timeout on windows can corrupt serial stream, best to implent this in software

                data = self._stream.read(self.READ_SIZE)
                if self._stop_event.is_set():
                    return
                now = time.time()
                dt=now-self._last_sample_time
                if not data and dt>timeout:
                    # Timeout with no data - finalize current test
                    self._finalize_current_test()
                    continue

                # Decode and add to buffer
                try:
                    text = data.decode('ascii')
                except UnicodeDecodeError:
                    # Non-ASCII data - mark current test as error
                    self._handle_error("Received non-ASCII data")
                    continue
                
                self._buffer += text
                #convert windows line endings to unix line endings if they're present
                self._buffer = self._buffer.replace("\r\n","\n")
                self._process_buffer(now)

        except StreamDisconnected as e:
            logger.debug("disconnect: %s", e.reason)
            self._finalize_current_test()
            self._queue.put(('disconnect', e.reason))

    def _process_buffer(self, timestamp):
        """Parse complete lines from buffer, create samples."""
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            line = line.strip()
            if not line:
                continue

            try:
                value = float(line)
            except ValueError:
                self._handle_error("Invalid float: {0}".format(line))
                continue

            self._add_sample(value, timestamp)

    def _add_sample(self, value, timestamp):
        """Add a sample (test start is handled by TestSession)."""
        # Track gap for adaptive timeout
        self._sample_count +=1
        if self._sample_count>=2:
            gap = timestamp - self._last_sample_time
            if gap > self._max_gap_this_test:
                self._max_gap_this_test = gap
        self._last_sample_time = timestamp

        # Push sample event
        self._queue.put(('sample', value, timestamp))
        logger.debug("sample: %.6f @ %.6f", value, timestamp)

    def _finalize_current_test(self):
        """Complete the current test if one is in progress."""
        if self._sample_count:
            #check the buffer for a complete sample with no following newline
            if self._buffer:
                self._buffer+="\n"
                self._process_buffer(time.time())
            self._queue.put(('complete',))
            logger.debug("test complete")
            self.reset()

    def _handle_error(self, message):
        """Handle an error condition."""
        logger.debug("error: %s", message)
        if self._sample_count:
            self._queue.put(('error', message))
            self.reset()
