"""Explicit boxed-answer extraction and version-locked Math-Verify scoring."""

from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import re
import threading


_scoring_pool = None
_scoring_pool_lock = threading.Lock()


def boxed_answer(text):
    """Last box only; an unfinished/empty last box is an incomplete answer."""
    matches = list(re.finditer(r"\\boxed\s*\{", text))
    if not matches:
        return None
    start = matches[-1].end()
    depth = 1
    for index in range(start, len(text)):
        if text[index] not in "{}":
            continue
        backslashes, previous = 0, index - 1
        while previous >= 0 and text[previous] == "\\":
            backslashes += 1
            previous -= 1
        if backslashes % 2:
            continue
        depth += 1 if text[index] == "{" else -1
        if depth == 0:
            return text[start:index].strip() or None
    return None


@lru_cache(maxsize=4096)
def parsed_answer(answer):
    from math_verify import LatexExtractionConfig, parse

    return parse(
        "\\boxed{" + answer + "}",
        extraction_config=[LatexExtractionConfig(boxed_match_priority=0)],
        fallback_mode="first_match",
        extraction_mode="first_match",
        parsing_timeout=5,
    )


def math_correct(gold, prediction):
    if prediction is None:
        return False
    if threading.current_thread() is not threading.main_thread():
        # Math-Verify uses SIGALRM for bounded parsing/verification. A spawned
        # process executes it on its main thread, without disabling the timeouts
        # or forking a process that already owns a CUDA context.
        global _scoring_pool
        with _scoring_pool_lock:
            if _scoring_pool is None:
                _scoring_pool = ProcessPoolExecutor(
                    max_workers=1, mp_context=multiprocessing.get_context("spawn")
                )
        return _scoring_pool.submit(math_correct, gold, prediction).result()
    from math_verify import verify

    return bool(
        verify(
            parsed_answer(gold),
            parsed_answer(prediction),
            float_rounding=6,
            numeric_precision=15,
            strict=True,
            timeout_seconds=5,
        )
    )


def natural_answer(text, row):
    from .core import extract_choice

    if row.get("answer_format") != "math":
        return extract_choice(text, row["choices"])
    answer = boxed_answer(text)
    # A grade is an ordinal label, not a symbolic exponent. Restrict this
    # normalization to questions explicitly asking which/what grade.
    if answer and re.search(r"\b(?:which|what)\s+grade\b", row.get("question", ""), re.I):
        ordinal = re.fullmatch(
            r"(\d+)(?:\^\{\\(?:text|mathrm)\{(st|nd|rd|th)\}\}|(st|nd|rd|th))",
            answer,
        )
        if ordinal:
            number = int(ordinal[1])
            suffix = (
                "th"
                if 10 <= number % 100 <= 20
                else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
            )
            if (ordinal[2] or ordinal[3]) == suffix:
                return ordinal[1]
    return answer
