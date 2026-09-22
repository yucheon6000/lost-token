"""Exact short-cycle diagnostics; no tag-name heuristic for semantic repetition."""

from __future__ import annotations

import re


def repeated_suffix(ids, spec):
    """Return the next token continuing an established exact cycle, if present."""
    if not spec["enabled"] or len(ids) < spec["min_span_tokens"]:
        return None
    for period in range(1, spec["max_period_tokens"] + 1):
        cycles = max(spec["min_cycles"], (spec["min_span_tokens"] + period - 1) // period)
        span = period * cycles
        if len(ids) < span:
            continue
        pattern = ids[-period:]
        if ids[-span:] == pattern * cycles:
            return {
                "period": period,
                "cycles": cycles,
                "span_tokens": span,
                "pattern": list(pattern),
                "blocked_token": pattern[0],
            }
    return None


def repetition_summary(ids, max_period):
    """Longest exact consecutive periodic span, computed without quadratic windows."""
    best = {"longest_span_tokens": 0, "period": None, "end_position": None}
    for period in range(1, min(max_period, len(ids) // 2) + 1):
        equal = 0
        for index in range(period, len(ids)):
            equal = equal + 1 if ids[index] == ids[index - period] else 0
            if equal >= period and equal + period > best["longest_span_tokens"]:
                best = {
                    "longest_span_tokens": equal + period,
                    "period": period,
                    "end_position": index + 1,
                }
    return best


def memory_markup_summary(text):
    tags = re.compile(r"</?possibilities>")
    total = len(tags.findall(text))
    structural = sum(
        len(tags.findall(line))
        for line in text.splitlines()
        if re.fullmatch(r"[ \t]*(?:</?possibilities>[ \t]*)+", line)
    )
    return {"structural_tags": structural, "inline_mentions": total - structural}
