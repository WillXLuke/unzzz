"""CSV import for multiple-choice questions."""

from __future__ import annotations

import unittest

from unzzz.question_csv import QuestionCsvError, parse_choice_csv


class ChoiceCsvTests(unittest.TestCase):
    def test_four_options_and_letters(self) -> None:
        rows = parse_choice_csv(
            "question,option a,option b,option c,option d,correct answer\n"
            "Which one is a colour?,Red,Green,Blue,Yellow,b\n"
        )
        self.assertEqual(rows, [{
            "question": "Which one is a colour?",
            "options": ["Red", "Green", "Blue", "Yellow"],
            "answer": "Green",
            "kind": "choice",
        }])

    def test_no_header_and_answer_text(self) -> None:
        rows = parse_choice_csv("2+2?,3,4,5,4")
        self.assertEqual(rows[0]["options"], ["3", "4", "5"])
        self.assertEqual(rows[0]["answer"], "4")

    def test_quoted_commas_bom_and_semicolon(self) -> None:
        rows = parse_choice_csv(
            "\ufeffquestion;option a;option b;correct answer\n"
            '"Which is red, exactly?";Red;Blue;a\n'
        )
        self.assertEqual(rows[0]["question"], "Which is red, exactly?")
        self.assertEqual(rows[0]["answer"], "Red")

    def test_answer_out_of_range(self) -> None:
        with self.assertRaisesRegex(QuestionCsvError, "correct answer"):
            parse_choice_csv("Q,a,b,c,d,f")

    def test_missing_option(self) -> None:
        with self.assertRaisesRegex(QuestionCsvError, "option"):
            parse_choice_csv("Q,a,,c,d,b")

    def test_duplicate_options(self) -> None:
        with self.assertRaisesRegex(QuestionCsvError, "unique"):
            parse_choice_csv("Q,a,A,c,d,a")

    def test_not_enough_options(self) -> None:
        with self.assertRaisesRegex(QuestionCsvError, "2-6 options"):
            parse_choice_csv("Q,a,b")

    def test_empty(self) -> None:
        with self.assertRaisesRegex(QuestionCsvError, "empty"):
            parse_choice_csv("\n")


if __name__ == "__main__":
    unittest.main()
