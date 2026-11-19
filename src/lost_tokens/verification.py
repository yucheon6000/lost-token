"""Gold-blind scheduling of bounded checks on the single continuing stream.

Cosine filtering only nominates a possible disagreement. The continuing model
must identify whether there is a substantive conflict and test it; no heuristic
here claims that text diversity implies a logical contradiction or correctness.
"""

import re


def validate_verification(exp):
    spec = exp.get("disagreement_verification")
    if spec is None:
        return
    keys = {"tokens", "max_checks", "min_body_tokens", "min_interval_tokens", "instruction"}
    if not isinstance(spec, dict) or set(spec) != keys:
        raise ValueError("Invalid disagreement_verification fields")
    for key in keys - {"instruction"}:
        floor = 0 if key in ("min_body_tokens", "min_interval_tokens") else 1
        if type(spec[key]) is not int or spec[key] < floor:
            raise ValueError("Invalid disagreement_verification." + key)
    if (
        not isinstance(spec["instruction"], str)
        or not spec["instruction"].strip()
        or re.search(r"</?(?:possibilities|think|reasoning)>", spec["instruction"], re.I)
    ):
        raise ValueError("Invalid disagreement_verification.instruction")


def verification_plan(exp, arm, event, previous, position, phase, eos_ids, cap):
    """Inputs contain only local generation state, never questions or gold answers."""
    spec = exp.get("disagreement_verification")
    if spec is None or arm != "filtered_futures" or phase != "thinking":
        return None
    if not event["retained_ranks"] or event["body_position"] < spec["min_body_tokens"]:
        return None
    checks = [e["verification"] for e in previous if e.get("verification")]
    if len(checks) >= spec["max_checks"]:
        return None
    if checks and position - checks[-1]["body_position"] < spec["min_interval_tokens"]:
        return None
    # A terminal preview is never turned into a new answer candidate or reopened.
    if any(
        (p.get("stop_marker") and p["stop_marker"].startswith("</"))
        or (p["ids"] and p["ids"][-1] in eos_ids)
        for p in event["previews"]
        if p["rank"] == event["selected_rank"] or p["rank"] in event["retained_ranks"]
    ):
        return None
    limit = cap
    forcing = exp.get("ours_budget_forcing")
    if forcing:
        limit = min(limit, forcing["force_at_body_tokens"])
    count = min(spec["tokens"], limit - position)
    if count <= 0:
        return None
    return {
        "body_position": position,
        "tokens": count,
        "text": "\n[Local verification task]\n" + spec["instruction"].strip() + "\n",
    }
