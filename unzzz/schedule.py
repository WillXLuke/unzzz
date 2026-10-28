"""Alarm scheduling math, special-day calendars and challenge questions.

All instants are epoch seconds (UTC).  Wall-clock arithmetic happens in the
configured IANA timezone so DST transitions behave correctly.
"""

from __future__ import annotations

import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,39}$")

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MODES = ("standard", "challenge")
DIFFICULTIES = ("easy", "normal", "hard")
QUESTION_SOURCES = ("auto", "custom")
CHALLENGE_TYPES = ("math", "text", "choice", "random_choice", "color", "pattern")
CUSTOM_TYPES = ("text", "choice", "random_choice")
QUESTION_KINDS = ("text", "choice")
COMPLETION_MODES = ("all", "count")
MAX_ALARM_USERS = 6
STATES_LIVE = ("ringing", "snoozed")

# Root-level shortlinks share the namespace with the panel.
RESERVED_SLUGS = {
    "api", "s", "qr", "healthz", "app.js", "style.css", "challenge.js",
    "alarm.js", "favicon.svg", "media", "static", "login", "setup", "admin",
    "favicon.ico", "robots.txt",
}

_rng = secrets.SystemRandom()


def load_timezone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return ZoneInfo("UTC")


def detect_system_timezone() -> str:
    """Best-effort detection of the host timezone without third-party deps."""
    for path in ("/etc/timezone", "/var/db/Timezone"):
        try:
            raw = Path(path).read_text(encoding="utf-8").strip()
            if raw:
                try:
                    ZoneInfo(raw)
                    return raw
                except (ZoneInfoNotFoundError, ValueError):
                    pass
        except OSError:
            continue
    # /etc/localtime is usually a symlink into /usr/share/zoneinfo
    try:
        import os

        target = os.path.realpath("/etc/localtime")
        marker = "/zoneinfo/"
        if marker in target:
            candidate = target.split(marker, 1)[1]
            ZoneInfo(candidate)
            return candidate
    except OSError:
        pass
    return "UTC"


def now_local(tz: ZoneInfo, ts: float | None = None) -> datetime:
    return datetime.fromtimestamp(ts, tz) if ts is not None else datetime.now(tz)


def _day_is_active(
    day: date, days_mask: int, calendar: dict[str, str] | None
) -> bool:
    """Calendar overrides the weekly pattern for dates it knows about.

    A date marked ``working`` rings even on a Sunday (Chinese 调休), and a
    date marked ``holiday`` is skipped even on a Monday.
    """
    if calendar:
        kind = calendar.get(day.isoformat())
        if kind == "working":
            return True
        if kind == "holiday":
            return False
    return bool(days_mask & (1 << (day.isoweekday() - 1)))


def next_occurrence(
    *,
    hhmm: str,
    days_mask: int,
    once_date: str | None,
    tz: ZoneInfo,
    after_ts: float | None = None,
    calendar: dict[str, str] | None = None,
) -> float | None:
    """Next epoch instant strictly after *after_ts* (default: now)."""
    now_ts = now_local(tz).timestamp() if after_ts is None else after_ts
    now = now_local(tz, now_ts)
    hour, minute = (int(x) for x in hhmm.split(":"))

    if not days_mask:
        if not once_date:
            return None
        try:
            d = date.fromisoformat(once_date)
        except ValueError:
            return None
        candidate = datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz)
        if candidate.timestamp() > now_ts:
            return candidate.timestamp()
        return None

    # A year of holidays is allowed, so scan generously.
    for offset in range(0, 400):
        day = now.date() + timedelta(days=offset)
        if not _day_is_active(day, days_mask, calendar):
            continue
        candidate = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
        if candidate.timestamp() > now_ts:
            return candidate.timestamp()
    return None


def days_to_mask(days: list[int] | None) -> int:
    mask = 0
    for d in days or []:
        if isinstance(d, bool) or not isinstance(d, int) or not (1 <= d <= 7):
            raise ValueError("days must be ISO weekdays 1-7 (Mon-Sun)")
        mask |= 1 << (d - 1)
    return mask


def mask_to_days(mask: int) -> list[int]:
    return [i + 1 for i in range(7) if mask & (1 << i)]


def format_days(mask: int, once_date: str | None) -> str:
    days = mask_to_days(mask)
    if not days:
        return f"Once on {once_date}" if once_date else "Never"
    if mask == 0b1111111:
        return "Every day"
    if mask == 0b0011111:
        return "Weekdays"
    if mask == 0b1100000:
        return "Weekends"
    return " ".join(DAY_NAMES[d - 1] for d in days)


def human_next(ts: float | None, tz: ZoneInfo, now_ts: float | None = None) -> str:
    if ts is None:
        return "not scheduled"
    now = now_local(tz, now_ts)
    target = now_local(tz, ts)
    delta = int(round((ts - now.timestamp()) / 60))
    if delta < 1:
        return "in less than a minute"
    if delta < 60:
        return f"in {delta} min"
    if delta < 60 * 24:
        h, m = divmod(delta, 60)
        return f"in {h}h {m}m" if m else f"in {h}h"
    days = (target.date() - now.date()).days
    if days == 1:
        return f"tomorrow at {target.strftime('%H:%M')}"
    if days < 7:
        return f"{DAY_NAMES[target.weekday()]} at {target.strftime('%H:%M')}"
    return target.strftime("%a %d %b at %H:%M")


def iso_local(ts: float | None, tz: ZoneInfo) -> str | None:
    if ts is None:
        return None
    return now_local(tz, ts).isoformat(timespec="seconds")


def random_slug() -> str:
    return "alarm-" + secrets.token_hex(4)


# ---------------------------------------------------------------- questions
def make_question(difficulty: str = "normal") -> tuple[str, str]:
    """Return (question_text, answer_string). Answers are never negative."""
    if difficulty not in DIFFICULTIES:
        difficulty = "normal"
    if difficulty == "easy":
        kind = _rng.choice(["add", "sub", "mul", "add"])
        if kind == "add":
            a, b = _rng.randint(6, 30), _rng.randint(6, 30)
            return f"{a} + {b}", str(a + b)
        if kind == "sub":
            a = _rng.randint(15, 45)
            b = _rng.randint(2, a - 1)
            return f"{a} − {b}", str(a - b)
        a, b = _rng.randint(2, 9), _rng.randint(2, 9)
        return f"{a} × {b}", str(a * b)

    if difficulty == "hard":
        kind = _rng.choice(["mul", "muladd", "mulsplit"])
        a, b = _rng.randint(6, 19), _rng.randint(6, 19)
        if kind == "mul":
            return f"{a} × {b}", str(a * b)
        c = _rng.randint(3, 25)
        if kind == "muladd":
            return f"{a} × {b} + {c}", str(a * b + c)
        c = _rng.randint(1, a * b - 1)
        return f"{a} × {b} − {c}", str(a * b - c)

    kind = _rng.choice(["mul", "add3", "sub", "mulsub"])
    if kind == "add3":
        a, b, c = _rng.randint(11, 49), _rng.randint(11, 49), _rng.randint(2, 19)
        return f"{a} + {b} + {c}", str(a + b + c)
    if kind == "sub":
        a, b = _rng.randint(30, 99), _rng.randint(10, 29)
        return f"{a} − {b}", str(a - b)
    a, b = _rng.randint(3, 12), _rng.randint(3, 12)
    if kind == "mulsub":
        c = _rng.randint(1, a * b - 1)
        return f"{a} × {b} − {c}", str(a * b - c)
    return f"{a} × {b}", str(a * b)


def parse_answer(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        text = raw.strip().replace(",", "")
        if re.fullmatch(r"-?\d{1,9}", text):
            return int(text)
    return None


def normalize_text_answer(raw: object) -> str | None:
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        return None
    value = " ".join(str(raw).strip().split()).casefold()
    return value or None


def answers_match(raw: object, expected: str, answer_type: str = "number") -> bool:
    if answer_type == "text":
        got = normalize_text_answer(raw)
        want = normalize_text_answer(expected)
        return got is not None and got == want
    value = parse_answer(raw)
    return value is not None and str(value) == str(expected).strip()


# --------------------------------------------------------------- validation
def validate_alarm_payload(
    data: dict,
    *,
    tz: ZoneInfo,
    users: list[dict] | None = None,
    question_count: int = 0,
    question_counts: dict[str, int] | None = None,
    calendar: dict[str, str] | None = None,
    auto_slug: str | None = None,
) -> tuple[dict | None, str | None]:
    """Validate a create/update alarm request. Returns (clean, error).

    ``users`` is the full user list; it is used for participant validation.
    ``calendar`` is the selected special-days map (date -> working|holiday).
    """
    if not isinstance(data, dict):
        return None, "Invalid request body"
    users = users or []

    label = str(data.get("label", "Alarm")).strip()
    if not (1 <= len(label) <= 60):
        return None, "Label must be 1-60 characters"

    hhmm = str(data.get("time", "")).strip()
    if not TIME_RE.match(hhmm):
        return None, "Time must be HH:MM (24-hour)"

    raw_days = data.get("days") or []
    if not isinstance(raw_days, list):
        return None, "days must be a list of weekdays"
    try:
        mask = days_to_mask(raw_days)
    except ValueError as exc:
        return None, str(exc)

    once_date = data.get("once_date") or None
    if once_date is not None:
        once_date = str(once_date).strip()
        if not DATE_RE.match(once_date):
            return None, "once_date must be YYYY-MM-DD"
        try:
            date.fromisoformat(once_date)
        except ValueError:
            return None, "once_date is not a real date"
    if mask and once_date:
        return None, "Choose repeat days or a one-time date, not both"
    if not mask and not once_date:
        return None, "Choose repeat days or a one-time date"

    enabled = bool(data.get("enabled", True))
    mode = str(data.get("mode", "standard"))
    if mode not in MODES:
        return None, "mode must be standard or challenge"
    difficulty = str(data.get("difficulty", "normal"))
    if difficulty not in DIFFICULTIES:
        return None, "difficulty must be easy, normal or hard"

    def clamp_int(key: str, default: int, lo: int, hi: int) -> tuple[int, str | None]:
        try:
            value = int(data.get(key, default))
        except (TypeError, ValueError):
            return default, f"{key} must be a number"
        if not (lo <= value <= hi):
            return default, f"{key} must be between {lo} and {hi}"
        return value, None

    snooze_minutes, err = clamp_int("snooze_minutes", 9, 1, 30)
    if err:
        return None, err
    max_snoozes, err = clamp_int("max_snoozes", 2, 0, 5)
    if err:
        return None, err
    max_ring_minutes, err = clamp_int("max_ring_minutes", 15, 1, 120)
    if err:
        return None, err

    # ---------------------------------------------------------- participants
    user_by_id = {int(u["id"]): u for u in users}
    participants: list[int] = []
    if mode == "challenge":
        raw_participants = data.get("participants", None)
        if raw_participants is None:
            # Backwards-compatible default: the first six active users.
            participants = [
                int(u["id"]) for u in users if u.get("active")
            ][:MAX_ALARM_USERS]
        else:
            if not isinstance(raw_participants, list):
                return None, "participants must be a list of user ids"
            seen = set()
            for raw_id in raw_participants:
                if isinstance(raw_id, bool):
                    return None, "participants must be user ids"
                try:
                    uid = int(raw_id)
                except (TypeError, ValueError):
                    return None, "participants must be user ids"
                if uid not in user_by_id:
                    return None, "One of the selected users no longer exists"
                if uid in seen:
                    continue
                seen.add(uid)
                participants.append(uid)
            if len(participants) > MAX_ALARM_USERS:
                return None, f"An alarm can select at most {MAX_ALARM_USERS} users"
            if not participants:
                return None, "Select at least one active user for a challenge alarm"
        active_selected = [uid for uid in participants if user_by_id[uid].get("active")]
        if enabled and not active_selected:
            return None, "Select at least one active user for a challenge alarm"

    completion_mode = str(data.get("completion_mode", "all"))
    if completion_mode not in COMPLETION_MODES:
        return None, "completion_mode must be all or count"
    if mode != "challenge":
        completion_mode = "all"
    target_count = 1
    if mode == "challenge" and completion_mode == "count":
        raw_target = data.get("target_count", 1)
        try:
            target_count = int(raw_target)
        except (TypeError, ValueError):
            return None, "target_count must be a number"
        if not participants:
            return None, "Select participants before setting a target"
        if not (1 <= target_count <= len(participants)):
            return None, f"target_count must be between 1 and {len(participants)}"

    challenge_type = str(
        data.get("challenge_type")
        or ("text" if data.get("question_source") == "custom" else "math")
    )
    if challenge_type not in CHALLENGE_TYPES:
        return None, "Unknown challenge type"
    if mode != "challenge":
        challenge_type = "math"
    try:
        challenge_count = int(data.get("challenge_count", 1))
    except (TypeError, ValueError):
        return None, "Challenges per person must be a whole number"
    if not (1 <= challenge_count <= 10):
        return None, "Challenges per person must be between 1 and 10"
    if mode != "challenge":
        challenge_count = 1
    question_source = "custom" if challenge_type in CUSTOM_TYPES else "auto"
    counts = dict(question_counts or {})
    if question_count:
        counts.setdefault("text", int(question_count))
    if enabled and mode == "challenge" and challenge_type in CUSTOM_TYPES:
        pool_kind = "choice" if challenge_type == "random_choice" else challenge_type
        if counts.get(pool_kind, 0) < 1:
            label = "text" if pool_kind == "text" else "multiple-choice"
            return None, f"Add at least one {label} question before using this type"

    # ----------------------------------------------------------------- music
    music_id = data.get("music_id")
    if music_id in (None, "", 0, "0"):
        music_id = None
    else:
        try:
            music_id = int(music_id)
        except (TypeError, ValueError):
            return None, "music_id must be a number"

    # ---------------------------------------------------------- special days
    calendar_id = data.get("calendar_id")
    if calendar_id in (None, "", 0, "0") or not mask:
        calendar_id = None
        calendar = None
    else:
        try:
            calendar_id = int(calendar_id)
        except (TypeError, ValueError):
            return None, "calendar_id must be a number"

    # ------------------------------------------------------------------ slug
    slug = None
    if mode == "challenge":
        raw_slug = str(data.get("slug") or "").strip().lower()
        if raw_slug:
            if not SLUG_RE.match(raw_slug):
                return None, "Shortlink must be 3-40 chars: a-z, 0-9, - or _"
            if raw_slug in RESERVED_SLUGS:
                return None, "That shortlink is reserved"
            slug = raw_slug
        else:
            slug = (auto_slug or random_slug()).lower()
            if not SLUG_RE.match(slug):
                slug = random_slug()
            if slug in RESERVED_SLUGS:
                slug = random_slug()

    # --------------------------------------------------------------- next run
    next_fire = None
    if enabled:
        next_fire = next_occurrence(
            hhmm=hhmm,
            days_mask=mask,
            once_date=once_date if not mask else None,
            tz=tz,
            calendar=calendar,
        )
        if next_fire is None:
            if not mask:
                return None, "That one-time date/time is in the past"
            if calendar_id:
                return None, "No future active day in this special-days calendar"
            return None, "No future alarm day"

    clean = {
        "label": label,
        "time": hhmm,
        "days_mask": mask,
        "once_date": once_date if not mask else None,
        "enabled": enabled,
        "mode": mode,
        "difficulty": difficulty,
        "snooze_minutes": snooze_minutes,
        "max_snoozes": max_snoozes,
        "max_ring_minutes": max_ring_minutes,
        "participants": participants,
        "completion_mode": completion_mode,
        "target_count": target_count,
        "question_source": question_source,
        "challenge_type": challenge_type,
        "challenge_count": challenge_count,
        "music_id": music_id,
        "calendar_id": calendar_id,
        "slug": slug,
        "next_fire": next_fire,
    }
    return clean, None
