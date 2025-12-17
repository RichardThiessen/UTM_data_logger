# SPDX-License-Identifier: MIT
"""Tests for models module."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utm_data_logger.models import Test, TestSession


class TestTestClass(unittest.TestCase):
    """Tests for Test object."""

    def test_initial_state(self):
        """Test initial state of a new Test."""
        test = Test()
        self.assertEqual(test.status, Test.STATUS_IN_PROGRESS)
        self.assertIsNone(test.error_message)
        self.assertIsNone(test.unit)
        self.assertEqual(test.sample_count, 0)
        self.assertEqual(test.values, [])
        self.assertEqual(test.timestamps, [])

    def test_unit_attribute(self):
        """Test that unit can be set on construction."""
        test = Test(unit='gf')
        self.assertEqual(test.unit, 'gf')

    def test_add_sample(self):
        """Test adding samples."""
        test = Test()
        test.add_sample(10.5, 1000.0)
        test.add_sample(20.3, 1000.1)

        self.assertEqual(test.values, [10.5, 20.3])
        self.assertEqual(test.timestamps, [1000.0, 1000.1])

    def test_values_and_timestamps_are_lists(self):
        """Test that values and timestamps are lists."""
        test = Test()
        test.add_sample(1.0, 1000.0)

        self.assertIsInstance(test.values, list)
        self.assertIsInstance(test.timestamps, list)

    def test_update_calculates_stats(self):
        """Test that update() calculates stats."""
        test = Test()
        test.add_sample(10.0, 1000.0)
        test.add_sample(5.0, 1000.1)
        test.add_sample(20.0, 1000.2)
        test.update()

        self.assertEqual(test.sample_count, 3)
        self.assertEqual(test.min_value, 5.0)
        self.assertEqual(test.max_value, 20.0)

    def test_stdev(self):
        """Test standard deviation calculation."""
        test = Test()
        # Values with known stdev of 2.0
        for v in [2, 4, 4, 4, 5, 5, 7, 9]:
            test.add_sample(float(v), 1000.0)
        test.update()

        self.assertAlmostEqual(test.stdev, 2.0)

    def test_estimated_rate(self):
        """Test sample rate estimation."""
        test = Test()
        # 10 samples at 10 Hz
        for i in range(10):
            test.add_sample(float(i), 1000.0 + i * 0.1)
        test.update()

        self.assertIsNotNone(test.estimated_rate)
        self.assertAlmostEqual(test.estimated_rate, 10.0, places=1)

    def test_estimated_duration(self):
        """Test duration estimation."""
        test = Test()
        # 100 samples at 10 Hz should be ~10 seconds
        for i in range(100):
            test.add_sample(float(i), 1000.0 + i * 0.1)
        test.update()

        self.assertIsNotNone(test.estimated_duration)
        self.assertAlmostEqual(test.estimated_duration, 10.0, places=1)


class TestTestSessionEventProcessing(unittest.TestCase):
    """Tests for TestSession event processing."""

    def test_initial_state(self):
        """Test initial state."""
        s = TestSession()
        self.assertEqual(s.tests, [])
        self.assertIsNone(s._active_test)
        self.assertFalse(s.is_connected)

    def test_sample_event_creates_test(self):
        """Test that sample event creates a new test."""
        s = TestSession()
        s.queue.put(('sample', 1.0, 1000.0))
        s.process_events()

        self.assertEqual(len(s.tests), 1)
        self.assertIsNotNone(s._active_test)
        self.assertEqual(s.tests[0].values, [1.0])

    def test_multiple_samples(self):
        """Test multiple samples in same test."""
        s = TestSession()
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('sample', 2.0, 1000.1))
        s.queue.put(('sample', 3.0, 1000.2))
        s.process_events()

        self.assertEqual(len(s.tests), 1)
        self.assertEqual(s.tests[0].values, [1.0, 2.0, 3.0])

    def test_complete_event(self):
        """Test complete event marks test as complete."""
        s = TestSession()
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('complete',))
        s.process_events()

        self.assertEqual(len(s.tests), 1)
        self.assertEqual(s.tests[0].status, Test.STATUS_COMPLETE)
        self.assertIsNone(s._active_test)

    def test_error_event(self):
        """Test error event marks test as error."""
        s = TestSession()
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('error', 'Bad data'))
        s.process_events()

        self.assertEqual(len(s.tests), 1)
        self.assertEqual(s.tests[0].status, Test.STATUS_ERROR)
        self.assertEqual(s.tests[0].error_message, 'Bad data')
        self.assertIsNone(s._active_test)

    def test_disconnect_event(self):
        """Test disconnect event completes test and sets reason."""
        s = TestSession()
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('disconnect', 'Connection lost'))
        s.process_events()

        self.assertEqual(s.tests[0].status, Test.STATUS_COMPLETE)
        self.assertEqual(s.disconnect_reason, 'Connection lost')

    def test_multiple_tests(self):
        """Test multiple test cycles."""
        s = TestSession()
        # First test
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('complete',))
        # Second test
        s.queue.put(('sample', 2.0, 2000.0))
        s.queue.put(('complete',))
        s.process_events()

        self.assertEqual(len(s.tests), 2)
        self.assertEqual(s.tests[0].values, [1.0])
        self.assertEqual(s.tests[1].values, [2.0])

    def test_delete_test(self):
        """Test deleting a test."""
        s = TestSession()
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('complete',))
        s.queue.put(('sample', 2.0, 2000.0))
        s.queue.put(('complete',))
        s.process_events()

        t1 = s.tests[0]
        s.delete_test(t1)

        self.assertEqual(len(s.tests), 1)
        self.assertEqual(s.tests[0].values, [2.0])

    def test_clear_all(self):
        """Test clearing all tests."""
        s = TestSession()
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('complete',))
        s.queue.put(('sample', 2.0, 2000.0))
        s.queue.put(('complete',))
        s.process_events()

        s.clear_all()
        self.assertEqual(s.tests, [])

    def test_active_test_survives_delete(self):
        """Test that active test keeps receiving samples after delete."""
        s = TestSession()
        # Start a test
        s.queue.put(('sample', 1.0, 1000.0))
        s.process_events()

        # Get the active test and delete it from list
        active = s._active_test
        s.delete_test(active)

        # Test is gone from list but still active
        self.assertEqual(len(s.tests), 0)
        self.assertIs(s._active_test, active)

        # More samples still go to it
        s.queue.put(('sample', 2.0, 1000.1))
        s.process_events()

        self.assertEqual(active.values, [1.0, 2.0])

    def test_start_event_creates_test_with_unit(self):
        """Test that start event creates a test with unit."""
        s = TestSession()
        s.queue.put(('start', 'gf'))
        s.queue.put(('sample', 1.0, 1000.0))
        s.process_events()

        self.assertEqual(len(s.tests), 1)
        self.assertEqual(s.tests[0].unit, 'gf')
        self.assertEqual(s.tests[0].values, [1.0])

    def test_start_event_with_no_unit(self):
        """Test that start event with None unit works."""
        s = TestSession()
        s.queue.put(('start', None))
        s.queue.put(('sample', 1.0, 1000.0))
        s.process_events()

        self.assertEqual(len(s.tests), 1)
        self.assertIsNone(s.tests[0].unit)
        self.assertEqual(s.tests[0].values, [1.0])

    def test_multiple_tests_with_different_units(self):
        """Test multiple tests with different units."""
        s = TestSession()
        # First test with gf
        s.queue.put(('start', 'gf'))
        s.queue.put(('sample', 1.0, 1000.0))
        s.queue.put(('complete',))
        # Second test with N
        s.queue.put(('start', 'N'))
        s.queue.put(('sample', 2.0, 2000.0))
        s.queue.put(('complete',))
        s.process_events()

        self.assertEqual(len(s.tests), 2)
        self.assertEqual(s.tests[0].unit, 'gf')
        self.assertEqual(s.tests[1].unit, 'N')


if __name__ == '__main__':
    unittest.main()
