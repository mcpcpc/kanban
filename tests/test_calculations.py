"""Unit tests for kanban.utils.calculations — pure functions, no DB required."""

import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parents[1] / 'src'))

from kanban.utils.calculations import parse_barcode, build_30_day_trend


class TestParseBarcode(unittest.TestCase):
    """Tests for parse_barcode()."""

    def test_k_prefix_valid(self):
        """K-prefixed barcodes like K000012 should return the numeric ID."""
        self.assertEqual(parse_barcode("K000012"), 12)

    def test_k_prefix_lowercase(self):
        """Lowercase k prefix should also be accepted."""
        self.assertEqual(parse_barcode("k000042"), 42)

    def test_plain_integer(self):
        """Plain integer strings should return the integer value."""
        self.assertEqual(parse_barcode("99"), 99)

    def test_leading_trailing_whitespace(self):
        """Whitespace around the barcode should be stripped."""
        self.assertEqual(parse_barcode("  K000007  "), 7)

    def test_invalid_format_letters(self):
        """Non-numeric content after the K prefix should return None."""
        self.assertIsNone(parse_barcode("KABC"))

    def test_invalid_format_random_string(self):
        """Completely non-numeric strings should return None."""
        self.assertIsNone(parse_barcode("NOT_A_BARCODE"))

    def test_empty_string(self):
        """Empty string should return None."""
        self.assertIsNone(parse_barcode(""))

    def test_whitespace_only(self):
        """Whitespace-only string should return None."""
        self.assertIsNone(parse_barcode("   "))

    def test_k_prefix_with_large_id(self):
        """Large IDs should be parsed correctly."""
        self.assertEqual(parse_barcode("K001234"), 1234)


class TestBuild30DayTrend(unittest.TestCase):
    """Tests for build_30_day_trend()."""

    def test_returns_exactly_30_entries(self):
        """Result list must always contain exactly 30 entries."""
        trend, _ = build_30_day_trend([])
        self.assertEqual(len(trend), 30)

    def test_empty_input_all_zeros(self):
        """With no rows, every day should have count == 0."""
        trend, _ = build_30_day_trend([])
        for entry in trend:
            self.assertEqual(entry["count"], 0)

    def test_max_value_at_least_one_on_empty(self):
        """max_value must be at least 1 even when all counts are zero."""
        _, max_value = build_30_day_trend([])
        self.assertGreaterEqual(max_value, 1)

    def test_sparse_data_fills_missing_days(self):
        """Days not in input should appear with count 0."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Provide only today; all other 29 days should default to 0.
        class FakeRow(dict):
            def __getitem__(self, key):
                return super().__getitem__(key)

        rows = [{"day": today, "count": 5}]
        trend, _ = build_30_day_trend(rows)
        zeros = [e for e in trend if e["day"] != today]
        for entry in zeros:
            self.assertEqual(entry["count"], 0)

    def test_sparse_data_correct_count_for_present_day(self):
        """Days that are in input should carry their count."""
        today = datetime.now().strftime("%Y-%m-%d")
        rows = [{"day": today, "count": 7}]
        trend, _ = build_30_day_trend(rows)
        today_entry = next(e for e in trend if e["day"] == today)
        self.assertEqual(today_entry["count"], 7)

    def test_max_value_reflects_highest_count(self):
        """max_value should equal the highest count in the window."""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = [
            {"day": today, "count": 10},
            {"day": yesterday, "count": 3},
        ]
        _, max_value = build_30_day_trend(rows)
        self.assertEqual(max_value, 10)

    def test_days_are_consecutive_and_in_order(self):
        """The 30 day window should be in ascending chronological order."""
        trend, _ = build_30_day_trend([])
        dates = [entry["day"] for entry in trend]
        self.assertEqual(dates, sorted(dates))

    def test_last_day_is_today(self):
        """The last entry in the trend should be today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        trend, _ = build_30_day_trend([])
        self.assertEqual(trend[-1]["day"], today)

    def test_first_day_is_29_days_ago(self):
        """The first entry should be 29 days ago."""
        expected_first = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
        trend, _ = build_30_day_trend([])
        self.assertEqual(trend[0]["day"], expected_first)


if __name__ == "__main__":
    unittest.main()
