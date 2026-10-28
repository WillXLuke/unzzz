"""Special-day CSV parsing."""

from __future__ import annotations

import unittest

from unzzz.special_days import (
    CalendarParseError,
    calendar_summary,
    normalize_kind,
    parse_calendar_csv,
)


class KindTests(unittest.TestCase):
    def test_english_and_chinese_types(self) -> None:
        for raw in ("working", "work", "on", "1", "上班", "工作", "调休", "补班", "调休上班"):
            self.assertEqual(normalize_kind(raw), "working", raw)
        for raw in ("holiday", "off", "rest", "0", "休", "休息", "放假", "节假日", "调休休息"):
            self.assertEqual(normalize_kind(raw), "holiday", raw)
        self.assertIsNone(normalize_kind("maybe"))


class CsvTests(unittest.TestCase):
    def test_header_and_notes(self) -> None:
        days = parse_calendar_csv(
            "date,type,note\n"
            "2026-01-01,holiday,New Year\n"
            "2026-01-04,working,Make-up day\n"
        )
        self.assertEqual(len(days), 2)
        self.assertEqual(days[0], {"date": "2026-01-01", "kind": "holiday", "note": "New Year"})
        self.assertEqual(days[1]["kind"], "working")

    def test_chinese_header_and_types(self) -> None:
        days = parse_calendar_csv(
            "日期,类型,备注\n"
            "2026/2/15,休息,春节\n"
            "2026/2/28,调休上班,补班\n"
        )
        self.assertEqual([d["date"] for d in days], ["2026-02-15", "2026-02-28"])
        self.assertEqual([d["kind"] for d in days], ["holiday", "working"])

    def test_bom_comments_tabs_and_compact_dates(self) -> None:
        days = parse_calendar_csv(
            "\ufeff# generated\n"
            "20260101\tholiday\n"
            "2026年1月4日\tworking\n"
        )
        self.assertEqual([d["date"] for d in days], ["2026-01-01", "2026-01-04"])
        self.assertEqual(summary := calendar_summary(days), {
            "day_count": 2,
            "working_days": 1,
            "holiday_days": 1,
            "first_date": "2026-01-01",
            "last_date": "2026-01-04",
        })
        self.assertEqual(summary["working_days"], 1)

    def test_duplicates_last_wins(self) -> None:
        days = parse_calendar_csv(
            "2026-01-01,holiday\n2026-01-01,working\n"
        )
        self.assertEqual(days, [{"date": "2026-01-01", "kind": "working", "note": ""}])

    def test_bad_rows_raise(self) -> None:
        with self.assertRaisesRegex(CalendarParseError, "invalid date"):
            parse_calendar_csv("date,type\n2026-13-40,holiday\n")
        with self.assertRaisesRegex(CalendarParseError, "type"):
            parse_calendar_csv("date,type\n2026-01-01,maybe\n")
        with self.assertRaisesRegex(CalendarParseError, "empty"):
            parse_calendar_csv("")
        with self.assertRaisesRegex(CalendarParseError, "at least date and type"):
            parse_calendar_csv("2026-01-01\n")

    def test_header_optional(self) -> None:
        days = parse_calendar_csv("2026-05-01,holiday\n2026-05-02,work\n")
        self.assertEqual([d["kind"] for d in days], ["holiday", "working"])

    def test_canonical_work_and_rest(self) -> None:
        days = parse_calendar_csv(
            "date,type,note\n"
            "2026-06-01,work,Make-up day\n"
            "2026-06-02,rest,Rest day\n"
        )
        self.assertEqual([d["kind"] for d in days], ["working", "holiday"])
        self.assertEqual(days[0]["note"], "Make-up day")


if __name__ == "__main__":
    unittest.main()
