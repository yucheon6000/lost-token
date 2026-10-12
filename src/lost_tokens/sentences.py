"""Incremental prose boundaries, excluding mathematical and code punctuation."""

import re


PUNCTUATION = ".!?。！？"
ABBREVIATION = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof|vs|etc|e\.g|i\.e|a\.m|p\.m)$", re.I)
INITIALISM = re.compile(r"\b(?:[A-Za-z]\.)+[A-Za-z]$")
FACTORIAL = re.compile(r"(?:\d|[)}\]]|(?<!\w)[A-Za-z])$")


class SentenceCounter:
    """Retain math/code state across tokens, with no rollout-length cap.

    An optional prefix seeds lexical state when a fork starts inside a formula.
    Only punctuation generated after that prefix contributes to the count.
    """

    def __init__(self, prefix=""):
        self.text = ""
        self.position = 0
        self.zone = None
        self.boundaries = set()
        self.minimum = len(prefix)
        self.feed(prefix)

    def feed(self, text, replace=0):
        previous = len(self.boundaries)
        if replace:
            cut = len(self.text) - replace
            removed = self.text[cut:]
            self.text = self.text[:cut]
            # Unicode decoding can replace an incomplete trailing character.
            # If a lexical delimiter changed, reconstruct the state rather than
            # retaining an invalid math/code mode. This is a rare fallback.
            if any(c in removed for c in "\\$`" + PUNCTUATION):
                self.position, self.zone, self.boundaries = 0, None, set()
            else:
                self.position = min(self.position, cut)
                self.boundaries = {p for p in self.boundaries if p < cut}
        self.text += text
        self._scan()
        return len(self.boundaries) - previous

    def _scan(self):
        text = self.text
        while self.position < len(text):
            start = self.position
            char = text[start]
            if self.zone is not None:
                if text.startswith(self.zone, start):
                    self.position += len(self.zone)
                    self.zone = None
                elif self.zone.startswith(text[start:]):
                    break  # A closing delimiter can span tokens.
                elif char == "\\" and not self.zone.startswith("`"):
                    if start + 1 == len(text):
                        break
                    self.position += 2
                else:
                    self.position += 1
                continue
            if char in "$`":
                end = start + 1
                while end < len(text) and text[end] == char:
                    end += 1
                if end == len(text):
                    break  # Distinguish $/$$ and inline/fenced backticks.
                self.zone = text[start:end]
                self.position = end
                continue
            if char == "\\":
                if start + 1 == len(text):
                    break
                if text[start + 1] in "([":
                    self.zone = "\\" + (")" if text[start + 1] == "(" else "]")
                self.position += 2
                continue
            if char not in PUNCTUATION:
                self.position += 1
                continue
            end = start + 1
            while end < len(text) and text[end] in PUNCTUATION:
                end += 1
            punctuation = text[start:end]
            if any(c in punctuation for c in "。！？"):
                if start >= self.minimum:
                    self.boundaries.add(start)
                # Keep the group pending so a later punctuation token cannot
                # count the same group twice. CJK endings need no whitespace.
                if end == len(text):
                    break
                self.position = end
                continue
            separator = end
            while separator < len(text) and text[separator] in "\"'”’)]}`":
                separator += 1
            if separator == len(text):
                break
            prefix = text[max(0, start - 128) : start]
            excluded = (
                punctuation == "."
                and (
                    ABBREVIATION.search(prefix)
                    or INITIALISM.search(prefix)
                    or (
                        re.fullmatch(r"[ \t]*\d+", prefix.rsplit("\n", 1)[-1])
                        and text[end] in " \t"
                    )
                )
            ) or (set(punctuation) == {"!"} and FACTORIAL.search(prefix))
            if start >= self.minimum and text[separator].isspace() and not excluded:
                self.boundaries.add(start)
            self.position = end


def sentence_starts(text):
    counter = SentenceCounter()
    counter.feed(text)
    return counter.boundaries
