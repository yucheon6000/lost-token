import unittest

from lost_tokens.core import extract_choice


class ChoiceExtractionTests(unittest.TestCase):
    choices = ["A", "B", "C", "D"]

    def test_plain_and_markdown_final_answers(self):
        for text in (
            "Final answer: (A)",
            "**Final answer**: (A)",
            "**Final answer:** (A)",
            "Final answer: **(A)**",
            "__Final answer__: (A)",
            "__Final answer:__ (A)",
            "Final answer: __(A)__",
            "final ANSWER: (a)",
        ):
            with self.subTest(text=text):
                self.assertEqual(extract_choice(text, self.choices), "A")

    def test_last_explicit_answer_wins_including_markdown_correction(self):
        self.assertEqual(
            extract_choice("Final answer: (A)\n**Final answer**: (B)", self.choices), "B"
        )
        self.assertEqual(
            extract_choice("**Final answer**: (B)\nFinal answer: (A)", self.choices), "A"
        )

    def test_does_not_guess_from_prose_or_option_words(self):
        for text in ("I considered (A), (B), and (C).", "Final answer: Apple", "(A)"):
            with self.subTest(text=text):
                self.assertIsNone(extract_choice(text, self.choices))

    def test_last_answer_must_be_an_allowed_choice(self):
        self.assertIsNone(extract_choice("Final answer: (Z)", self.choices))
        self.assertIsNone(extract_choice("Final answer: (A)\n**Final answer**: (Z)", self.choices))
