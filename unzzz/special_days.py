"""CSV import for special-day calendars.

The canonical format is::

    date,type,note
    2026-01-01,holiday,New Year
    2026-01-04,work,Make-up workday

``work`` (or ``working``) marks a working day; ``holiday`` (or ``rest``) marks
a rest day.  The note is optional.  Comma, semicolon and tab separators are
accepted, as is an optional header row.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

MAX_ROWS = 4000

_DATE_SEPARATORS = re.compile(r"^\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*$")
_DATE_CN = re.compile(r"^\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?\s*$")
_DATE_COMPACT = re.compile(r"^\s*(\d{8})\s*$")

WORKING_WORDS = {
    "1", "true", "yes", "on", "work", "working", "workday", "office",
    "上班", "工作", "工作日", "调休", "补班", "调休上班", "班",
}
HOLIDAY_WORDS = {
    "0", "false", "no", "off", "rest", "holiday", "vacation",
    "休", "休息", "放假", "假", "假日", "节假日", "假期",
}

DATE_HEADERS = {"date", "day", "日期", "日付", "时间"}
TYPE_HEADERS = {"type", "kind", "类型", "班休", "工作/假期", "工作日/假期"}
NOTE_HEADERS = {"note", "name", "remark", "备注", "说明", "名称"}


class CalendarParseError(ValueError):
    pass


def _decode(text: str) -> str:
    return text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def _split_rows(text: str) -> list[tuple[int, list[str]]]:
    lines = text.split("\n")
    sample = "\n".join(line for line in lines[:5] if line.strip())
    delimiter = ","
    if sample:
        counts = {d: sample.count(d) for d in (",", ";", "\t")}
        delimiter = max(counts, key=counts.get)
        if counts[delimiter] == 0:
            delimiter = ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows: list[tuple[int, list[str]]] = []
    for line_no, row in enumerate(reader, start=1):
        cells = [c.strip() for c in row]
        if not any(cells):
            continue
        if cells[0].startswith("#"):
            continue
        rows.append((line_no, cells))
    return rows


def _normalize_date(raw: str) -> str | None:
    value = raw.strip()
    match = _DATE_SEPARATORS.match(value) or _DATE_CN.match(value)
    if match:
        year, month, day = (int(x) for x in match.groups())
    else:
        match = _DATE_COMPACT.match(value)
        if not match:
            return None
        compact = match.group(1)
        year, month, day = int(compact[:4]), int(compact[4:6]), int(compact[6:8])
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def normalize_kind(raw: str) -> str | None:
    value = raw.strip().lower()
    compact = re.sub(r"\s+", "", value)
    if value in WORKING_WORDS or compact in WORKING_WORDS:
        return "working"
    if value in HOLIDAY_WORDS or compact in HOLIDAY_WORDS:
        return "holiday"
    if "班" in compact or "work" in compact:
        return "working"
    if any(ch in compact for ch in ("休", "假")) or "holiday" in compact or compact == "off":
        return "holiday"
    return None


def parse_calendar_csv(text: str) -> list[dict]:
    if not isinstance(text, str):
        raise CalendarParseError("CSV must be text")
    rows = _split_rows(_decode(text))
    if not rows:
        raise CalendarParseError("The CSV is empty")
    if len(rows) > MAX_ROWS:
        raise CalendarParseError(f"Too many rows (maximum {MAX_ROWS})")

    date_idx, type_idx, note_idx = 0, 1, 2
    header = [c.lower() for c in rows[0][1]]
    if (
        any(c in DATE_HEADERS for c in header)
        and any(c in TYPE_HEADERS for c in header)
    ):
        for i, cell in enumerate(header):
            if cell in DATE_HEADERS:
                date_idx = i
            elif cell in TYPE_HEADERS:
                type_idx = i
            elif cell in NOTE_HEADERS:
                note_idx = i
        rows = rows[1:]

    if not rows:
        raise CalendarParseError("The CSV has no data rows")

    by_date: dict[str, dict] = {}
    for line_no, cells in rows:
        if max(date_idx, type_idx) >= len(cells):
            raise CalendarParseError(f"Line {line_no}: expected at least date and type")
        iso = _normalize_date(cells[date_idx])
        if iso is None:
            raise CalendarParseError(f"Line {line_no}: invalid date {cells[date_idx]!r}")
        kind = normalize_kind(cells[type_idx])
        if kind is None:
            raise CalendarParseError(
                f"Line {line_no}: type must be work/working or holiday/rest, "
                f"got {cells[type_idx]!r}"
            )
        note = cells[note_idx] if note_idx < len(cells) else ""
        by_date[iso] = {"date": iso, "kind": kind, "note": note[:120]}

    if not by_date:
        raise CalendarParseError("No valid days found")
    return [by_date[key] for key in sorted(by_date)]


def calendar_summary(days: list[dict]) -> dict:
    working = sum(1 for d in days if d["kind"] == "working")
    return {
        "day_count": len(days),
        "working_days": working,
        "holiday_days": len(days) - working,
        "first_date": days[0]["date"] if days else None,
        "last_date": days[-1]["date"] if days else None,
    }
