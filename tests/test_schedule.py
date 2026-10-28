"""Unit tests for scheduling and challenge questions (stdlib unittest)."""

from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from unzzz.schedule import (
    answers_match,
    days_to_mask,
    format_days,
    make_question,
    mask_to_days,
    next_occurrence,
    parse_answer,
    validate_alarm_payload,
)


class NextOccurrenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tz = ZoneInfo("UTC")

    def dt(self, ts: float) -> datetime:
        return datetime.fromtimestamp(ts, self.tz)

    def test_weekday_same_day(self) -> None:
        # Monday 26 Oct 2026, 06:00 UTC
        after = datetime(2026, 10, 26, 6, 0, tzinfo=self.tz).timestamp()
        nf = next_occurrence(
            hhmm="07:30", days_mask=days_to_mask([1, 2, 3, 4, 5]), once_date=None,
            tz=self.tz, after_ts=after,
        )
        self.assertEqual(self.dt(nf).strftime("%Y-%m-%d %H:%M"), "2026-10-26 07:30")

    def test_weekday_rolls_to_next_day(self) -> None:
        after = datetime(2026, 10, 26, 8, 0, tzinfo=self.tz).timestamp()
        nf = next_occurrence(
            hhmm="07:30", days_mask=days_to_mask([1, 2, 3, 4, 5]), once_date=None,
            tz=self.tz, after_ts=after,
        )
        self.assertEqual(self.dt(nf).strftime("%Y-%m-%d %H:%M"), "2026-10-27 07:30")

    def test_friday_rolls_to_monday(self) -> None:
        after = datetime(2026, 10, 30, 8, 0, tzinfo=self.tz).timestamp()
        nf = next_occurrence(
            hhmm="07:30", days_mask=days_to_mask([1, 2, 3, 4, 5]), once_date=None,
            tz=self.tz, after_ts=after,
        )
        self.assertEqual(self.dt(nf).strftime("%Y-%m-%d %H:%M"), "2026-11-02 07:30")

    def test_one_time_future_and_past(self) -> None:
        after = datetime(2026, 10, 26, 6, 0, tzinfo=self.tz).timestamp()
        nf = next_occurrence(
            hhmm="07:30", days_mask=0, once_date="2026-10-26", tz=self.tz, after_ts=after,
        )
        self.assertEqual(self.dt(nf).strftime("%H:%M"), "07:30")
        past = next_occurrence(
            hhmm="05:30", days_mask=0, once_date="2026-10-26", tz=self.tz, after_ts=after,
        )
        self.assertIsNone(past)

    def test_dst_spring_forward_and_fall_back(self) -> None:
        tz = ZoneInfo("Europe/Berlin")
        # 28 March 2026 12:00 UTC; DST starts on the 29th.
        after = datetime(2026, 3, 28, 12, 0, tzinfo=ZoneInfo("UTC")).timestamp()
        nf = next_occurrence(
            hhmm="07:30", days_mask=0b1111111, once_date=None, tz=tz, after_ts=after,
        )
        local = datetime.fromtimestamp(nf, tz)
        self.assertEqual(local.strftime("%Y-%m-%d %H:%M %z"), "2026-03-29 07:30 +0200")
        # 24 October 2026; DST ends on the 25th.
        after = datetime(2026, 10, 24, 12, 0, tzinfo=ZoneInfo("UTC")).timestamp()
        nf = next_occurrence(
            hhmm="07:30", days_mask=0b1111111, once_date=None, tz=tz, after_ts=after,
        )
        local = datetime.fromtimestamp(nf, tz)
        self.assertEqual(local.strftime("%Y-%m-%d %H:%M %z"), "2026-10-25 07:30 +0100")

    def test_special_day_calendar_overrides_weekdays(self) -> None:
        # Monday 26 Oct 2026 is marked as a holiday, Tuesday as working.
        after = datetime(2026, 10, 26, 6, 0, tzinfo=self.tz).timestamp()
        nf = next_occurrence(
            hhmm="07:30",
            days_mask=days_to_mask([1, 2, 3, 4, 5]),
            once_date=None,
            tz=self.tz,
            after_ts=after,
            calendar={"2026-10-26": "holiday", "2026-10-27": "working"},
        )
        self.assertEqual(self.dt(nf).strftime("%Y-%m-%d %H:%M"), "2026-10-27 07:30")

    def test_working_weekend_rings_even_if_not_in_mask(self) -> None:
        # Sunday 1 Nov 2026 is marked as a make-up working day.
        after = datetime(2026, 10, 31, 12, 0, tzinfo=self.tz).timestamp()
        nf = next_occurrence(
            hhmm="07:30",
            days_mask=days_to_mask([1]),
            once_date=None,
            tz=self.tz,
            after_ts=after,
            calendar={"2026-11-01": "working"},
        )
        self.assertEqual(self.dt(nf).strftime("%Y-%m-%d %H:%M"), "2026-11-01 07:30")

    def test_days_helpers(self) -> None:
        mask = days_to_mask([1, 3, 5])
        self.assertEqual(mask_to_days(mask), [1, 3, 5])
        self.assertEqual(format_days(0b1111111, None), "Every day")
        self.assertEqual(format_days(0b0011111, None), "Weekdays")
        self.assertEqual(format_days(0, "2026-11-01"), "Once on 2026-11-01")


class AnswerMatchTests(unittest.TestCase):
    def test_numeric_and_text_answers(self) -> None:
        self.assertTrue(answers_match(" 042 ", "42", "number"))
        self.assertTrue(answers_match("Cat", "cat", "text"))
        self.assertTrue(answers_match("  New   York ", "new york", "text"))
        self.assertFalse(answers_match("dog", "cat", "text"))
        self.assertFalse(answers_match("nope", "42", "number"))


class QuestionTests(unittest.TestCase):
    def test_questions_are_arithmetic_and_answers_correct(self) -> None:
        for difficulty in ("easy", "normal", "hard"):
            for _ in range(200):
                question, answer = make_question(difficulty)
                expr = question.replace("×", "*").replace("−", "-")
                self.assertEqual(str(eval(expr, {"__builtins__": {}}, {})), answer, question)
                self.assertGreaterEqual(int(answer), 0, question)

    def test_parse_answer(self) -> None:
        self.assertEqual(parse_answer(" 42 "), 42)
        self.assertEqual(parse_answer("1,024"), 1024)
        self.assertEqual(parse_answer(-7), -7)
        self.assertIsNone(parse_answer("4.2"))
        self.assertIsNone(parse_answer(""))
        self.assertIsNone(parse_answer(True))
        self.assertIsNone(parse_answer("abc"))


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tz = ZoneInfo("Europe/Berlin")
        self.users = [
            {"id": 1, "name": "Ada", "active": 1},
            {"id": 2, "name": "Bob", "active": 1},
            {"id": 3, "name": "Cy", "active": 0},
        ]

    def base(self, **over):
        data = {
            "label": "Wake up",
            "time": "07:30",
            "days": [1, 2, 3, 4, 5],
            "once_date": None,
            "enabled": True,
            "mode": "standard",
            "difficulty": "normal",
            "snooze_minutes": 9,
            "max_snoozes": 2,
            "max_ring_minutes": 15,
        }
        data.update(over)
        return data

    def test_valid(self) -> None:
        clean, error = validate_alarm_payload(
            self.base(), tz=self.tz, users=self.users
        )
        self.assertIsNone(error)
        self.assertEqual(clean["days_mask"], 0b0011111)
        self.assertIsNotNone(clean["next_fire"])

    def test_challenge_needs_active_users(self) -> None:
        clean, error = validate_alarm_payload(
            self.base(mode="challenge", participants=[]),
            tz=self.tz,
            users=[],
        )
        self.assertIsNone(clean)
        self.assertIn("active user", error)

    def test_challenge_defaults_to_first_six_active_users(self) -> None:
        users = [{"id": i, "name": f"U{i}", "active": 1} for i in range(1, 9)]
        clean, error = validate_alarm_payload(
            self.base(mode="challenge"), tz=self.tz, users=users
        )
        self.assertIsNone(error)
        self.assertEqual(clean["participants"], [1, 2, 3, 4, 5, 6])

    def test_challenge_accepts_participants_and_target(self) -> None:
        clean, error = validate_alarm_payload(
            self.base(
                mode="challenge",
                participants=[1, 2],
                completion_mode="count",
                target_count=1,
            ),
            tz=self.tz,
            users=self.users,
        )
        self.assertIsNone(error)
        self.assertEqual(clean["target_count"], 1)
        _clean, error = validate_alarm_payload(
            self.base(
                mode="challenge",
                participants=[1, 2],
                completion_mode="count",
                target_count=3,
            ),
            tz=self.tz,
            users=self.users,
        )
        self.assertIn("target_count", error)

    def test_too_many_participants(self) -> None:
        users = [{"id": i, "name": f"U{i}", "active": 1} for i in range(1, 8)]
        _clean, error = validate_alarm_payload(
            self.base(mode="challenge", participants=list(range(1, 8))),
            tz=self.tz,
            users=users,
        )
        self.assertIn("at most 6", error)

    def test_custom_questions_required(self) -> None:
        _clean, error = validate_alarm_payload(
            self.base(mode="challenge", participants=[1], question_source="custom"),
            tz=self.tz,
            users=self.users,
            question_count=0,
        )
        self.assertIn("text question", error)
        clean, error = validate_alarm_payload(
            self.base(mode="challenge", participants=[1], challenge_type="text"),
            tz=self.tz,
            users=self.users,
            question_counts={"text": 2, "choice": 0},
        )
        self.assertIsNone(error)
        self.assertEqual(clean["challenge_type"], "text")
        self.assertEqual(clean["question_source"], "custom")

    def test_choice_and_generated_types(self) -> None:
        clean, error = validate_alarm_payload(
            self.base(mode="challenge", participants=[1], challenge_type="choice"),
            tz=self.tz,
            users=self.users,
            question_counts={"text": 1, "choice": 0},
        )
        self.assertIn("multiple-choice question", error)
        for kind in ("color", "pattern", "math"):
            clean, error = validate_alarm_payload(
                self.base(mode="challenge", participants=[1], challenge_type=kind),
                tz=self.tz,
                users=self.users,
                question_counts={"text": 0, "choice": 0},
            )
            self.assertIsNone(error, (kind, error))
            self.assertEqual(clean["challenge_type"], kind)

    def test_slug_is_generated_and_validated(self) -> None:
        clean, error = validate_alarm_payload(
            self.base(mode="challenge", participants=[1]),
            tz=self.tz,
            users=self.users,
        )
        self.assertIsNone(error)
        self.assertTrue(clean["slug"].startswith("alarm-"))
        _clean, error = validate_alarm_payload(
            self.base(mode="challenge", participants=[1], slug="api"),
            tz=self.tz,
            users=self.users,
        )
        self.assertIn("reserved", error)

    def test_days_and_date_are_exclusive(self) -> None:
        _clean, error = validate_alarm_payload(
            self.base(once_date="2030-01-01"), tz=self.tz, users=self.users
        )
        self.assertIn("not both", error)

    def test_missing_repeat(self) -> None:
        _clean, error = validate_alarm_payload(
            self.base(days=[]), tz=self.tz, users=self.users
        )
        self.assertIn("repeat days or a one-time date", error)

    def test_past_once_date(self) -> None:
        _clean, error = validate_alarm_payload(
            self.base(days=[], once_date="2000-01-01"),
            tz=self.tz,
            users=self.users,
        )
        self.assertIn("past", error)

    def test_bad_time_and_limits(self) -> None:
        for bad in ("7:30", "24:00", "07:60", "seven"):
            _clean, error = validate_alarm_payload(
                self.base(time=bad), tz=self.tz, users=self.users
            )
            self.assertIsNotNone(error)
        _clean, error = validate_alarm_payload(
            self.base(max_snoozes=99), tz=self.tz, users=self.users
        )
        self.assertIn("max_snoozes", error)


if __name__ == "__main__":
    unittest.main()
