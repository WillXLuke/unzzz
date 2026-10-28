"""Typed challenge generation and answer checking."""

from __future__ import annotations

import json
import unittest

from unzzz.challenge_types import (
    check_answer,
    generate_challenge,
    parse_choice_options,
    question_to_spec,
    valid_choice_options,
)


class ChallengeTypeTests(unittest.TestCase):
    def test_math_generation_and_check(self) -> None:
        spec = generate_challenge("math", "normal")
        self.assertEqual(spec["challenge_type"], "math")
        self.assertEqual(spec["answer_type"], "number")
        expr = spec["question"].replace("×", "*").replace("−", "-")
        self.assertEqual(str(int(eval(expr, {"__builtins__": {}}, {}))), spec["answer"])
        self.assertTrue(check_answer("math", spec["answer"], spec["answer"]))
        self.assertFalse(check_answer("math", spec["answer"], "999999"))

    def test_text_pool_generation(self) -> None:
        pool = [
            {"id": 1, "question": "Cat?", "answer": "Mochi", "kind": "text", "options": None},
            {"id": 2, "question": "Floor?", "answer": "3", "kind": "text", "options": None},
        ]
        spec = generate_challenge("text", "normal", pool)
        self.assertEqual(spec["challenge_type"], "text")
        self.assertIn(spec["question"], ("Cat?", "Floor?"))
        self.assertTrue(check_answer("text", spec["answer"], spec["answer"].upper()))
        self.assertFalse(check_answer("text", spec["answer"], "wrong"))

    def test_choice_pool_payload_and_check(self) -> None:
        pool = [{
            "id": 7, "question": "Pick blue", "answer": "Blue", "kind": "choice",
            "options": json.dumps(["Red", "Blue", "Green", "Yellow"]),
        }]
        spec = generate_challenge("choice", "normal", pool)
        self.assertEqual(spec["challenge_type"], "choice")
        self.assertEqual(spec["payload"]["options"], ["Red", "Blue", "Green", "Yellow"])
        self.assertTrue(check_answer("choice", "Blue", " blue "))
        self.assertFalse(check_answer("choice", "Blue", "Green"))
        self.assertFalse(check_answer("choice", "Blue", ""))

    def test_color_generation_and_check(self) -> None:
        spec = generate_challenge("color", "normal")
        self.assertEqual(spec["challenge_type"], "color")
        payload = spec["payload"]
        keys = [c["key"] for c in payload["options"]]
        self.assertEqual(len(keys), 4)
        self.assertIn(payload["target"]["key"], keys)
        self.assertTrue(check_answer("color", spec["answer"], spec["answer"]))
        wrong = next(k for k in keys if k != spec["answer"])
        self.assertFalse(check_answer("color", spec["answer"], wrong))

    def test_pattern_generation_and_check(self) -> None:
        spec = generate_challenge("pattern", "normal")
        self.assertEqual(spec["challenge_type"], "pattern")
        payload = spec["payload"]
        self.assertEqual(payload["size"], 3)
        self.assertEqual(len(payload["target"]), 4)
        self.assertTrue(check_answer("pattern", spec["answer"], payload["target"]))
        self.assertTrue(check_answer("pattern", spec["answer"], list(reversed(payload["target"]))))
        self.assertFalse(check_answer("pattern", spec["answer"], payload["target"][:-1]))
        self.assertFalse(check_answer("pattern", spec["answer"], []))

    def test_choice_option_validation(self) -> None:
        self.assertIsNone(valid_choice_options(["A", "B"]))
        self.assertIn("2-6", valid_choice_options(["A"]))
        self.assertIn("unique", valid_choice_options(["A", "a"]))
        options, error = parse_choice_options("A\nB\n\nC")
        self.assertIsNone(error)
        self.assertEqual(options, ["A", "B", "C"])
        options, error = parse_choice_options("one")
        self.assertIsNotNone(error)

    def test_question_to_spec(self) -> None:
        spec = question_to_spec({
            "id": 3, "question": "Q", "answer": "A", "kind": "choice",
            "options": '["A","B"]', "created_at": 0,
        })
        self.assertEqual(spec["answer_type"], "choice")
        self.assertEqual(spec["payload"], {"options": ["A", "B"]})
        self.assertEqual(spec["question_id"], 3)


if __name__ == "__main__":
    unittest.main()
