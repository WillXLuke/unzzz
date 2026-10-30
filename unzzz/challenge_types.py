"""Typed wake-up challenges: maths, text, multiple choice, colour, pattern."""

from __future__ import annotations

import json
import secrets
from typing import Any

from .schedule import (
    CHALLENGE_TYPES,
    CUSTOM_TYPES,
    QUESTION_KINDS,
    answers_match,
    make_question,
    normalize_text_answer,
)

TYPE_LABELS = {
    "math": "Generated maths",
    "text": "Text question",
    "choice": "Multiple choice",
    "random_choice": "Random multiple choice",
    "color": "Colour match",
    "pattern": "Pattern paint",
    "hold": "Button hold",
    "typing": "Typing test",
    "dice": "Roll dice",
}
COLORS = [
    {"key": "red", "name": "Red", "hex": "#ff5c5c"},
    {"key": "orange", "name": "Orange", "hex": "#ff9f43"},
    {"key": "yellow", "name": "Yellow", "hex": "#ffe066"},
    {"key": "lime", "name": "Lime", "hex": "#c8ff5e"},
    {"key": "green", "name": "Green", "hex": "#4ade80"},
    {"key": "teal", "name": "Teal", "hex": "#2dd4bf"},
    {"key": "cyan", "name": "Cyan", "hex": "#67e8f9"},
    {"key": "blue", "name": "Blue", "hex": "#60a5fa"},
    {"key": "indigo", "name": "Indigo", "hex": "#818cf8"},
    {"key": "violet", "name": "Violet", "hex": "#c084fc"},
    {"key": "pink", "name": "Pink", "hex": "#f472b6"},
    {"key": "brown", "name": "Brown", "hex": "#b08968"},
]

_rng = secrets.SystemRandom()


def _choice_options(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def parse_question(row: dict) -> dict:
    try:
        options = json.loads(row.get("options") or "[]")
    except (TypeError, ValueError):
        options = []
    return {
        "id": int(row["id"]),
        "question": row["question"],
        "answer": row["answer"],
        "kind": row.get("kind") or "text",
        "options": _choice_options(options),
        "created_at": row.get("created_at"),
    }


def question_to_spec(row: dict) -> dict:
    kind = row.get("kind") or "text"
    options = parse_question(row)["options"]
    payload = {"options": options} if kind == "choice" else {}
    return {
        "challenge_type": kind,
        "answer_type": kind,
        "question": row["question"],
        "answer": row["answer"],
        "payload": payload,
        "question_id": int(row["id"]),
    }


def _math(difficulty: str) -> dict:
    question, answer = make_question(difficulty)
    return {
        "challenge_type": "math",
        "answer_type": "number",
        "question": question,
        "answer": answer,
        "payload": {},
        "question_id": None,
    }


def _color(difficulty: str) -> dict:
    options = _rng.sample(COLORS, 4)
    target = _rng.choice(options)
    payload = {
        "target": {"key": target["key"], "name": target["name"], "hex": target["hex"]},
        "options": [
            {"key": c["key"], "name": c["name"], "hex": c["hex"]} for c in options
        ],
    }
    return {
        "challenge_type": "color",
        "answer_type": "color",
        "question": "Tap the swatch that matches the target.",
        "answer": target["key"],
        "payload": payload,
        "question_id": None,
    }


def _pattern(difficulty: str, size: int = 3) -> dict:
    size = size if size in (3, 6, 9) else 3
    count = {3: 4, 6: 8, 9: 12}.get(size, 4)
    target = sorted(_rng.sample(range(size * size), count))
    return {
        "challenge_type": "pattern",
        "answer_type": "pattern",
        "question": f"Paint the highlighted {size}×{size} pattern.",
        "answer": json.dumps(target),
        "payload": {"size": size, "target": target},
        "question_id": None,
    }


PHRASES = [
    "the quiet morning train waits beside the open gate",
    "seven blue birds landed softly on the garden wall",
    "my alarm clock finally learned to keep a secret",
    "warm bread and strong coffee are waiting downstairs",
    "the sleepy cat refused to move from the sunny chair",
    "a small green boat drifted past the old stone bridge",
    "the kitchen radio played a song about rainy days",
    "three golden leaves spun slowly across the empty road",
    "the morning sky looked like a fresh sheet of paper",
    "we packed apples bread and cheese for the long walk",
]


def _hold() -> dict:
    seconds = 5
    return {
        "challenge_type": "hold",
        "answer_type": "hold",
        "question": f"Press and hold the button for {seconds} seconds.",
        "answer": "held",
        "payload": {"seconds": seconds},
        "question_id": None,
    }


def _typing() -> dict:
    phrase = _rng.choice(PHRASES)
    return {
        "challenge_type": "typing",
        "answer_type": "text",
        "question": "Type this phrase exactly:",
        "answer": phrase,
        "payload": {"phrase": phrase, "max_words": 15},
        "question_id": None,
    }


def _dice() -> dict:
    target = _rng.randint(1, 6)
    return {
        "challenge_type": "dice",
        "answer_type": "dice",
        "question": f"Roll a six-sided die and get {target}.",
        "answer": str(target),
        "payload": {"target": target, "max_tries": 5},
        "question_id": None,
    }


def generate_challenge(
    kind: str,
    difficulty: str = "normal",
    pool: list[dict] | None = None,
    exclude_question_id: int | None = None,
    pattern_size: int = 3,
) -> dict:
    """Create one question/answer spec.  Falls back to maths if a pool is empty."""
    pool = pool or []
    if kind in CUSTOM_TYPES:
        candidates = [
            q for q in pool
            if (q.get("kind") or "text") == kind
            and int(q["id"]) != exclude_question_id
        ]
        if not candidates:
            candidates = [
                q for q in pool if (q.get("kind") or "text") == kind
            ]
        if candidates:
            return question_to_spec(_rng.choice(candidates))
    if kind == "color":
        return _color(difficulty)
    if kind == "pattern":
        return _pattern(difficulty, pattern_size)
    if kind == "hold":
        return _hold()
    if kind == "typing":
        return _typing()
    if kind == "dice":
        return _dice()
    return _math(difficulty)


def spec_payload(spec: dict) -> str | None:
    payload = spec.get("payload") or {}
    return json.dumps(payload, separators=(",", ":")) if payload else None


def payload_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def check_answer(challenge_type: str, expected: str, raw: Any) -> bool:
    kind = challenge_type or "math"
    if kind == "math":
        return answers_match(raw, expected, "number")
    if kind == "text":
        return answers_match(raw, expected, "text")
    if kind == "choice":
        got = normalize_text_answer(raw)
        want = normalize_text_answer(expected)
        return got is not None and got == want
    if kind == "color":
        return isinstance(raw, str) and raw.strip().lower() == expected.strip().lower()
    if kind == "hold":
        return isinstance(raw, str) and raw.strip().lower() == "held"
    if kind == "typing":
        return isinstance(raw, str) and raw.strip() == expected.strip()
    if kind == "dice":
        try:
            return int(raw) == int(expected)
        except (TypeError, ValueError):
            return False
    if kind == "pattern":
        if not isinstance(raw, list):
            return False
        try:
            got = sorted({int(x) for x in raw if not isinstance(x, bool)})
            want = sorted({int(x) for x in json.loads(expected)})
        except (TypeError, ValueError):
            return False
        return bool(got) and got == want
    return False


def valid_choice_options(options: list[str]) -> str | None:
    if not (2 <= len(options) <= 6):
        return "Multiple choice needs 2-6 options"
    if len({o.casefold() for o in options}) != len(options):
        return "Multiple-choice options must be unique"
    if any(len(o) > 80 for o in options):
        return "Each option must be 80 characters or fewer"
    return None


def parse_choice_options(raw: Any) -> tuple[list[str], str | None]:
    if isinstance(raw, list):
        options = [str(x).strip() for x in raw]
    elif isinstance(raw, str):
        options = [line.strip() for line in raw.splitlines()]
    else:
        options = []
    options = [o for o in options if o]
    error = valid_choice_options(options)
    return options, error
