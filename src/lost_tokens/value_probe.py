"""Re-sample the right side of an isolated arithmetic equality."""

import ast
from collections import Counter
from fractions import Fraction
import math
from operator import add, mul, sub, truediv
import re

from .core import derived_seed, digest


NUMBER = r"[+-]?(?:[0-9]{1,3}(?:,[0-9]{3}){1,3}|[0-9]{1,12})(?:\.[0-9]{1,10})?"
FRACTION = rf"\\frac\{{{NUMBER}\}}\{{{NUMBER}\}}"
EXPRESSION = rf"(?:[0-9.,()+*/^×÷−²³ \t-]|\\(?:times|cdot|div)|{FRACTION}){{3,100}}?"
# Fixed-width assertions let the anchor stay at the first mathematical symbol.
PROSE_START = r"(?<=so )|(?<=is )|(?<=be )|(?<=: )|(?<=, )|(?<=; )|(?<=gives )|(?<=that's )"
EQUALITY = re.compile(
    rf"(?P<opening>\$\$?|\\\(|\\\[|\n|(?<==)|{PROSE_START})"
    r"(?:(?<=\n)[ \t]*[-*][ \t]+)?[ \t]*"
    rf"(?P<left>{EXPRESSION})[ \t]*=[ \t]*"
    rf"(?P<value>{NUMBER}(?:[ \t]*/[ \t]*{NUMBER})?|{FRACTION})[ \t]*"
    r"(?P<closing>\$\$?|\\\)|\\\]|[.,;](?=[ \t\n])|(?=\n|\Z))",
    re.IGNORECASE,
)
CLOSING = {
    "$": ("$",), "$$": ("$$",), r"\(": (r"\)",), r"\[": (r"\]",),
    "\n": ("", ".", ",", ";"), "": ("$", "$$", r"\)", r"\]", "", ".", ",", ";"),
}
OPERATORS = {
    ast.Add: add, ast.Sub: sub, ast.Mult: mul, ast.Div: truediv,
}
NORMALIZE = (("×", "*"), (r"\times", "*"), (r"\cdot", "*"), ("÷", "/"), (r"\div", "/"),
             ("−", "-"), ("^", "**"), ("²", "**2"), ("³", "**3"))
FRACTION_RE = re.compile(rf"\\frac\{{({NUMBER})\}}\{{({NUMBER})\}}")
GROUPED_NUMBER = re.compile(r"(?<![0-9,])[0-9]{1,3}(?:,[0-9]{3}){1,3}(?![0-9,])")


def exact_arithmetic(source):
    """Evaluate a short numeric expression without executing Python."""
    expression = FRACTION_RE.sub(r"(\1/\2)", source)
    for original, normalized in NORMALIZE:
        expression = expression.replace(original, normalized)
    expression = GROUPED_NUMBER.sub(lambda match: match[0].replace(",", ""), expression).strip()

    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Fraction(ast.get_source_segment(expression, node))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            sign = -1 if isinstance(node.op, ast.USub) else 1
            return sign * evaluate(node.operand)
        if not isinstance(node, ast.BinOp):
            raise ValueError("Not numeric arithmetic")
        left, right = evaluate(node.left), evaluate(node.right)
        op = type(node.op)
        if op == ast.Pow and right.denominator == 1 and -8 <= right <= 8:
            value = left ** int(right)
        elif op in OPERATORS:
            value = OPERATORS[op](left, right)
        else:
            raise ValueError("Unsupported arithmetic operator")
        if max(abs(value.numerator), value.denominator) > 10**40:
            raise ValueError("Intermediate arithmetic value is too large")
        return value

    try:
        return evaluate(ast.parse(expression, mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError):
        return None


def validate_value_probe(exp):
    spec = exp.get("value_probe")
    if spec is None:
        return
    if (
        not isinstance(spec, dict)
        or set(spec) != {"samples", "max_per_case", "position"}
        or type(spec["samples"]) is not int
        or not 2 <= spec["samples"] <= 32
        or type(spec["max_per_case"]) is not int
        or not 1 <= spec["max_per_case"] <= 16
        or spec["position"] not in ("entropy", "first")
        or exp["branch_tokens"] < 2
    ):
        raise ValueError("Invalid value_probe settings")


def probe_for_arm(exp, arm):
    return exp.get("value_probe") if arm == "filtered_futures" else None


def equalities(text):
    for match in EQUALITY.finditer(text):
        complete = bool(match["closing"]) or match.end() < len(text)
        if complete and match["closing"] in CLOSING[match["opening"]]:
            yield match


def choose_position(preview, spec, decode, context_tail=()):
    """Probe a closed, inconsistent right side with a usable token boundary."""
    if preview["stop_marker"] or not preview["text"]:
        return None
    tail = list(context_tail)
    text = decode(tail + preview["ids"])
    positions = {}
    for match in equalities(text):
        expected = exact_arithmetic(match["left"])
        observed = exact_arithmetic(match["value"])
        if expected is None or observed is None or observed == expected:
            continue
        anchor = text[:match.start("value")].rstrip(" \t")
        positions[anchor] = {
            "anchor": anchor,
            "observed": str(observed),
            "expected": str(expected),
        }
    if not positions:
        return None
    boundaries = {}
    for offset in range(len(preview["ids"])):
        anchor = decode(tail + preview["ids"][:offset]).rstrip(" \t")
        if anchor in positions:
            boundaries[anchor] = offset
    eligible = [
        {**positions[anchor], "offset": offset, "entropy": preview["entropies"][offset]}
        for anchor, offset in boundaries.items()
    ]
    if spec["position"] == "first":
        return eligible[0] if eligible else None
    return max(eligible, key=lambda point: point["entropy"], default=None)


def probe_requests(context, body, seed, prefix, count, spec):
    root = digest(context + prefix)
    history = digest(body + prefix)
    return [
        {
            "root_sha256": root,
            "root_length": len(context) + len(prefix),
            "generated_history_sha256": history,
            "seed": derived_seed(seed, root, "value-probe", sample),
            "count": count,
        }
        for sample in range(spec["samples"])
    ]


def decide_probe(position, prefix, samples, decode, eos_ids, context_tail=()):
    values = []
    winner = None
    for index, sample in enumerate(samples):
        text = decode(list(context_tail) + prefix + sample["ids"])
        value = next(
            (
                exact_arithmetic(match["value"])
                for match in equalities(text)
                if text[:match.start("value")].rstrip(" \t") == position["anchor"]
            ),
            None,
        )
        value = str(value) if value is not None else None
        values.append(value)
        if (
            winner is None
            and value == position["expected"]
            and not sample["stop_marker"]
            and sample["ids"][-1] not in eos_ids
        ):
            winner = index
    counts = Counter(value for value in values if value is not None)
    total = sum(counts.values())
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
    return {
        **position,
        "sample_values": values,
        "value_entropy": entropy if total else None,
        "selected_sample": winner,
    }
