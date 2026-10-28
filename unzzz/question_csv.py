"""Import multiple-choice questions from a small CSV file."""

from __future__ import annotations

import csv
import io
import re

MAX_ROWS = 200
MAX_OPTIONS = 6


class QuestionCsvError(ValueError):
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
    rows: list[tuple[int, list[str]]] = []
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    for line_no, row in enumerate(reader, start=1):
        cells = [cell.strip() for cell in row]
        if not any(cells):
            continue
        if cells[0].startswith("#"):
            continue
        rows.append((line_no, cells))
    return rows


def _looks_like_header(cells: list[str]) -> bool:
    first = cells[0].strip().lower()
    if first not in {"question", "q", "问题", "質問"}:
        return False
    return any(re.search(r"(option|answer|correct|选项|答案)", c.lower()) for c in cells[1:])


def _answer_index(answer: str, options: list[str]) -> int | None:
    raw = answer.strip()
    low = raw.lower()
    letter = re.fullmatch(r"(?:option\s*)?([a-f])(?:[\).:\s]*)", low)
    if letter:
        index = ord(letter.group(1)) - ord("a")
        return index if index < len(options) else None
    if low.isdigit():
        index = int(low) - 1
        if 0 <= index < len(options):
            return index
    for index, option in enumerate(options):
        if option.casefold() == raw.casefold():
            return index
    return None


def parse_choice_csv(text: str) -> list[dict]:
    if not isinstance(text, str):
        raise QuestionCsvError("CSV must be text")
    rows = _split_rows(_decode(text))
    if not rows:
        raise QuestionCsvError("The CSV is empty")
    if len(rows) > MAX_ROWS:
        raise QuestionCsvError(f"Too many rows (maximum {MAX_ROWS})")

    option_indices: list[int]
    question_idx = 0
    answer_idx = -1
    if _looks_like_header(rows[0][1]):
        header = [c.strip().lower() for c in rows[0][1]]
        question_idx = next(
            (i for i, c in enumerate(header) if c in {"question", "q", "问题", "質問"}),
            0,
        )
        answer_idx = next(
            (i for i, c in enumerate(header) if re.search(r"(answer|correct|答案)", c)),
            len(header) - 1,
        )
        option_indices = [
            i for i, c in enumerate(header)
            if i not in (question_idx, answer_idx)
            and re.search(r"(option\s*[a-f]?|^[a-f]$|选项\s*[a-f]?)", c)
        ]
        rows = rows[1:]
    else:
        # Last column is the answer; the columns in between are options.
        option_indices = list(range(1, max(1, len(rows[0][1]) - 1)))
        answer_idx = len(rows[0][1]) - 1

    if not (2 <= len(option_indices) <= MAX_OPTIONS):
        raise QuestionCsvError("Each row needs 2-6 options")
    if not rows:
        raise QuestionCsvError("The CSV has no data rows")

    questions: list[dict] = []
    for line_no, cells in rows:
        if max(question_idx, answer_idx, *option_indices) >= len(cells):
            raise QuestionCsvError(f"Line {line_no}: not enough columns")
        question = cells[question_idx].strip()
        options = [cells[i].strip() for i in option_indices]
        answer_raw = cells[answer_idx].strip()
        if not question:
            raise QuestionCsvError(f"Line {line_no}: question is empty")
        if len(question) > 300:
            raise QuestionCsvError(f"Line {line_no}: question is too long")
        if any(not option for option in options):
            raise QuestionCsvError(f"Line {line_no}: every option must have a value")
        if any(len(option) > 80 for option in options):
            raise QuestionCsvError(f"Line {line_no}: an option is too long")
        if len({option.casefold() for option in options}) != len(options):
            raise QuestionCsvError(f"Line {line_no}: options must be unique")
        answer_index = _answer_index(answer_raw, options)
        if answer_index is None:
            raise QuestionCsvError(
                f"Line {line_no}: correct answer must be a letter from a-"
                f"{chr(ord('a') + len(options) - 1)}"
            )
        questions.append({
            "question": question,
            "options": options,
            "answer": options[answer_index],
            "kind": "choice",
        })
    return questions
