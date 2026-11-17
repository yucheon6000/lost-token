"""Gold-blind agreement over independently persisted complete responses.

This module cannot access a question's reference answer. It chooses an existing
member prediction; it never fabricates a merged reasoning trace or rewrites a
member's selected-rollout commits.
"""

from .math_scoring import math_correct


def answer_consensus(predictions, answer_format, choices=()):
    """Unweighted vote; ties use the earliest member in the frozen roster.

    Missing finals abstain. The denominator still includes every requested
    member. Math answers cluster by exact text or locked symbolic equivalence,
    never by correctness against a reference.
    """
    if answer_format not in ("math", "choice") or not predictions:
        raise ValueError("A non-empty prediction roster and supported format are required")
    groups, abstentions = [], []
    for index, prediction in enumerate(predictions):
        if prediction is None or not isinstance(prediction, str) or not prediction.strip():
            abstentions.append(index)
            continue
        prediction = prediction.strip()
        if answer_format == "choice" and prediction not in choices:
            abstentions.append(index)
            continue
        cluster = next(
            (
                group
                for group in groups
                if prediction == group["prediction"]
                or (answer_format == "math" and math_correct(group["prediction"], prediction))
            ),
            None,
        )
        if cluster is None:
            groups.append({"prediction": prediction, "members": [index]})
        else:
            cluster["members"].append(index)
    groups.sort(key=lambda group: (-len(group["members"]), group["members"][0]))
    best = groups[0] if groups else None
    return {
        "prediction": best["prediction"] if best else None,
        "selected_member": best["members"][0] if best else None,
        "groups": groups,
        "abstentions": abstentions,
        "requested_members": len(predictions),
        "valid_members": len(predictions) - len(abstentions),
        "support": len(best["members"]) if best else 0,
        "strict_majority": bool(best and len(best["members"]) > len(predictions) / 2),
        "tied": len(groups) > 1 and len(groups[0]["members"]) == len(groups[1]["members"]),
    }
