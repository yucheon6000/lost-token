"""Protocol helpers shared by execution, audits and numerical regression tests."""

from .core import RunStore
from .repetition import repetition_summary, memory_markup_summary


class RequestedPause(Exception):
    pass


class PausableStore(RunStore):
    def __init__(self, *args, stop_after_calls=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_after_calls = stop_after_calls

    def call(self, *args, **kwargs):
        result = super().call(*args, **kwargs)
        if self.stop_after_calls and self.calls >= self.stop_after_calls:
            raise RequestedPause("Requested interruption after an atomic checkpoint")
        return result


def planned_rows(spec, split, mode):
    if mode == "regression":
        rows = []
        for selected in spec["validation"]["regression_cases"]:
            candidates = split["tasks"][selected["task"]]["development"]
            row = next((r for r in candidates if r["id"] == selected["id"]), None)
            if row is None:
                raise ValueError("Regression case must be in the frozen development split")
            rows.append(("development/" + selected["task"], row))
        return rows
    if mode == "smoke":
        return [
            ("smoke/" + name, row)
            for name in spec["smoke"]["tasks"]
            for row in split["tasks"][name]["development"][: spec["smoke"]["cases_per_task"]]
        ]
    rows = []
    for phase in ("development", "evaluation"):
        # Round-robin tasks: interim results cover multiple task types early.
        selected = {t["name"]: split["tasks"][t["name"]][phase] for t in spec["datasets"]}
        if phase == "development":
            selected = {
                k: v[: spec["execution"]["development_cases_per_task"]] for k, v in selected.items()
            }
        for index in range(max(map(len, selected.values()))):
            for task, items in selected.items():
                if index < len(items):
                    rows.append((phase + "/" + task, items[index]))
    return rows


def development_check(cases, spec):
    arms = {}
    for arm in spec["experiment"]["arms"]:
        rows = [c["conditions"][arm] for c in cases]
        completion = sum(r["prediction"] is not None for r in rows) / len(rows) if rows else 0.0
        markup = [
            memory_markup_summary(r["body_text"], spec["experiment"].get("memory_format"))
            for r in rows
        ]
        repeat = [
            repetition_summary(
                r["body_ids"], spec["experiment"]["repetition_guard"]["max_period_tokens"]
            )
            for r in rows
        ]
        arms[arm] = {
            "n": len(rows),
            "answer_completion": completion,
            "structural_memory_tags": sum(m["structural_tags"] for m in markup),
            "inline_memory_mentions": sum(m["inline_mentions"] for m in markup),
            "longest_repetition_span": max((v["longest_span_tokens"] for v in repeat), default=0),
        }
    passed = all(
        r["answer_completion"] >= spec["execution"]["min_development_answer_completion"]
        and r["structural_memory_tags"]
        <= spec["execution"]["max_development_structural_memory_tags"]
        and r["longest_repetition_span"] < spec["execution"]["repetition_failure_span_tokens"]
        for r in arms.values()
    )
    return {
        "passed": passed,
        "arms": arms,
        "rule": "Completion, actual standalone memory delimiters, and consecutive short-cycle repetition only. Inline mentions and gold correctness do not determine passage.",
    }
