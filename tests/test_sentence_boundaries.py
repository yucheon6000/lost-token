"""Mathematical punctuation and long streaming spans must not shorten previews."""

import unittest

from lost_tokens.sentences import SentenceCounter, sentence_starts


class SentenceBoundaryTests(unittest.TestCase):
    def test_factorials_in_observed_failed_previews_are_not_endings(self):
        for text in (
            "We use 26! to compute. Done. ",
            "2! = 2 and n! / (n-1)! = n. Done. ",
            "64! / 65! = 1/65. Done. ",
            "D = (m-1)! (-1)^m (N-m)! as above. Done. ",
            "There are 26! permutations. Done. ",
        ):
            with self.subTest(text=text):
                self.assertEqual(len(sentence_starts(text)), 2)

    def test_factorial_followed_by_sentence_punctuation_still_ends_prose(self):
        for text in ("It is 26!. Done. ", "Is it n!? Yes! ", "Wow! Good! "):
            with self.subTest(text=text):
                self.assertEqual(len(sentence_starts(text)), 2)

    def test_math_code_and_escaped_punctuation_do_not_count(self):
        for span in (
            "$n! = 2. \\\\ x? y!$",
            "$$n! = 2. x? y!$$",
            r"\(n! = 2. x? y!\)",
            r"\[n! = 2. x? y!\]",
            "`x! = 2. y?`",
            "```python\nx = 2. # why?\n```",
            r"escaped \. \! \?",
        ):
            with self.subTest(span=span):
                self.assertEqual(len(sentence_starts(span + " First sentence. Second sentence. ")), 2)

    def test_every_character_cut_matches_whole_text(self):
        text = 'Dr. X uses $n! = 2. $$x?$$$ and `x! y?`. "Done?!" 次。！？Next. '
        expected = sentence_starts(text)
        for cut in range(len(text) + 1):
            with self.subTest(cut=cut):
                counter = SentenceCounter()
                counter.feed(text[:cut])
                counter.feed(text[cut:])
                self.assertEqual(counter.boundaries, expected)

    def test_long_math_and_code_spans_remain_open_across_many_chunks(self):
        for opening, closing in [("$", "$"), ("$$", "$$"), (r"\[", r"\]"), ("```", "```")]:
            counter = SentenceCounter()
            for char in opening + " x. y! z? " * 200 + closing + " First. Second. ":
                counter.feed(char)
            self.assertEqual(len(counter.boundaries), 2)

    def test_fork_mid_formula_inherits_lexical_state(self):
        counter = SentenceCounter("An old sentence. $" + "x " * 100)
        counter.feed("n! = 2. Still math? $ First. Second. ")
        self.assertEqual(len(counter.boundaries), 2)

    def test_cjk_group_is_not_recounted_when_extended(self):
        counter = SentenceCounter()
        self.assertEqual(counter.feed("終。"), 1)
        self.assertEqual(counter.feed("！？"), 0)
        self.assertEqual(counter.feed(" 次。"), 1)

    def test_empty_open_math_and_unicode_decoder_replacement(self):
        self.assertEqual(sentence_starts(""), set())
        self.assertEqual(sentence_starts("$unclosed math. ? ! "), set())
        counter = SentenceCounter()
        counter.feed("A �")
        counter.feed("한 sentence. Next. ", replace=1)
        self.assertEqual(len(counter.boundaries), 2)


if __name__ == "__main__":
    unittest.main()
