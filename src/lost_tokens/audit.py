"""Read-only ledger audit for every completed recurrent thinking condition."""

import argparse
import json
from pathlib import Path
import time
from types import SimpleNamespace

from transformers import AutoTokenizer, GenerationConfig

from lost_tokens.core import atomic_json, derived_seed, digest, file_digest, sum_cost
from lost_tokens.recurrent_memory import (
    compact_history,
    final_response,
    instruction,
    memory_text,
    reasoning_phase,
    emitted_marker,
    fragment_text,
)
from lost_tokens.protocol import planned_rows
from lost_tokens.cosine import cosine_matrix, select_distinct
from lost_tokens.repetition import repeated_suffix, repetition_summary, memory_markup_summary


def audit(run, partial=False, model=None):
    identity = json.loads((run / "identity.json").read_text(encoding="utf-8"))
    spec = identity["spec"]
    exp = spec["experiment"]
    split = json.loads((run / "split.json").read_text(encoding="utf-8"))
    assert digest(split) == identity["split_sha256"]
    assert json.loads(
        (run / "resolved-config.json").read_text(encoding="utf-8")) == spec
    for relative, sha in identity["source"].items():
        assert file_digest(run / "provenance" / relative) == sha
    if model is None:
        cfg = spec["model"]
        kwargs = {k: cfg[k]
                  for k in ("revision", "cache_dir", "local_files_only")}
        tok = AutoTokenizer.from_pretrained(
            cfg["name"], token=False, trust_remote_code=False, **kwargs
        )
        eos = GenerationConfig.from_pretrained(
            cfg["name"], token=False, **kwargs).eos_token_id
        model = SimpleNamespace(
            encode=lambda s: tok.encode(s, add_special_tokens=False),
            tokenizer=tok,
            decode=lambda ids: tok.decode(ids, skip_special_tokens=True),
            prompt=lambda s: tok.apply_chat_template(
                [{"role": "user", "content": s}],
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=True,
            ),
            special_ids=set(tok.all_special_ids),
            eos_ids=set(eos if isinstance(eos, list) else [eos]),
        )
    think_end = model.encode("</think>")[0]
    records, hashes, case_hashes = {}, {}, {}
    for path in (run / "checkpoints").glob("*.json"):
        saved = json.loads(path.read_text(encoding="utf-8"))
        p = saved["payload"]
        assert digest(p) == saved["sha256"]
        assert path.stem == digest(
            {"label": p["label"], "request": p["request"]})
        assert p["label"] not in records
        records[p["label"]] = p
        hashes[path.name] = file_digest(path)
    completed_conditions = events_count = completed_cases = 0
    started = last_log = time.monotonic()
    plans = planned_rows(spec, split, identity["mode"])
    for namespace, row in plans:
        base = model.prompt(instruction(row) + row["question"])
        seed = derived_seed(exp["seed"], namespace, row["id"])
        for arm in exp["arms"]:
            tag = f"{namespace}/{row['id']}/{arm}"
            if tag + "/complete" not in records:
                continue
            result = records[tag + "/complete"]["result"]
            assert records[tag + "/prefill"]["request"]["ids"] == base
            context = list(base)
            body = []
            history = []
            events = []
            checks = []
            costs = [records[tag + "/prefill"]["result"]]
            phase = reasoning_phase(model, base)
            has_reasoning_token = False
            step = 0
            compactions = []
            body_guards = []

            def check_guards(out, history, forced_first=False):
                expected = []
                for offset, token in enumerate(out["ids"]):
                    if forced_first and offset == 0:
                        continue
                    guard = repeated_suffix(
                        history + out["ids"][:offset], exp["repetition_guard"])
                    if guard and guard["blocked_token"] not in model.eos_ids | {think_end}:
                        assert token != guard["blocked_token"]
                        expected.append(
                            {"offset": offset, "sampled_token": token, **guard})
                assert out["guard_events"] == expected

            def segment(label, scan):
                record = records[tag + "/" + label]
                request, out = record["request"], record["result"]
                assert request["root_sha256"] == digest(context) and request["root_length"] == len(
                    context
                )
                assert request["generated_history_sha256"] == digest(body)
                assert (
                    request["body_position"] == len(body)
                    and request["seed"] == seed
                    and request["scan"] == scan
                )
                assert len(out["ids"]) <= request["count"]
                assert len(out["raw_log_probabilities"]) == len(out["ids"])
                assert not any(i in model.eos_ids or i ==
                               think_end for i in out["ids"][:-1])
                markers = [
                    emitted_marker(model, context + out["ids"][:i], token)
                    for i, token in enumerate(out["ids"])
                ]
                assert not any(markers[:-1])
                assert out["stop_marker"] == (markers[-1] if markers else None)
                check_guards(out, body)
                body_guards.extend(
                    {"body_position": len(body) + g["offset"], **g} for g in out["guard_events"]
                )
                if scan:
                    assert len(out["checks"]) == len(
                        out["ids"]) + (out["fork"] is not None)
                    assert [c["body_position"] for c in out["checks"]] == list(
                        range(len(body), len(body) + len(out["checks"]))
                    )
                    for index, check in enumerate(out["checks"]):
                        if check["eligible"]:
                            assert index == len(
                                out["checks"]) - 1 and out["fork"] is not None
                            assert {k: v for k, v in check.items() if k != "body_position"} == out[
                                "fork"
                            ]
                            items = check["items"]
                            assert len(items) >= 2 and items[0]["rank"] == 1
                            assert len({i["token_id"]
                                       for i in items}) == len(items)
                            assert all(
                                i["probability"] >= exp["min_candidate_probability"]
                                and i["token_id"] not in model.special_ids
                                for i in items
                            )
                            assert all(
                                a["probability"] >= b["probability"]
                                for a, b in zip(items, items[1:])
                            )
                            assert sum(i["probability"]
                                       for i in items) <= 1.00001
                else:
                    assert not out["checks"] and out["fork"] is None
                checks.extend(out["checks"])
                body.extend(out["ids"])
                context.extend(out["ids"])
                if out["ids"]:
                    history.append({"kind": "body", "ids": out["ids"]})
                costs.append(out)
                return out

            while len(body) < exp["max_output_tokens"] and (
                not body or body[-1] not in model.eos_ids
            ):
                memory_tokens = sum(len(h["ids"])
                                    for h in history if h["kind"] == "memory")
                compact_label = tag + f"/step-{step}/compact"
                if memory_tokens > exp["memory_capacity_tokens"] - exp["max_event_memory_tokens"]:
                    record = records[compact_label]
                    assert record["request"]["before_sha256"] == digest(
                        context)
                    history, removed = compact_history(
                        history, exp["memory_compact_to_tokens"])
                    context = base + [i for h in history for i in h["ids"]]
                    assert record["request"]["after_sha256"] == digest(context)
                    assert record["request"]["removed_events"] == removed
                    assert [i for h in history if h["kind"]
                            == "body" for i in h["ids"]] == body
                    costs.append(record["result"])
                    compactions.append(record["result"])
                else:
                    assert compact_label not in records
                scan = phase == "thinking" and has_reasoning_token and arm != "plain_ar"
                next_fork_position = (
                    (events[-1]["body_position"] +
                     exp["min_branch_interval_tokens"])
                    if events
                    else 0
                )
                expected_count = min(
                    exp["checkpoint_body_tokens"], exp["max_output_tokens"] -
                    len(body)
                )
                if phase == "thinking" and not has_reasoning_token:
                    expected_count = 1
                if scan and len(body) < next_fork_position:
                    expected_count = min(
                        expected_count, next_fork_position - len(body))
                    scan = False
                assert records[tag +
                               f"/step-{step}/scan"]["request"]["count"] == expected_count
                out = segment(f"step-{step}/scan", scan)
                marker = out["stop_marker"]
                if marker and marker.startswith("</"):
                    phase = "final"
                elif marker and phase == "waiting":
                    phase = "thinking"
                    has_reasoning_token = False
                elif phase == "thinking" and out["ids"]:
                    has_reasoning_token = True
                if out["fork"]:
                    event = records[tag +
                                    f"/event-{len(events)}/complete"]["result"]
                    assert event == result["events"][len(events)]
                    assert event["body_position"] == len(body) and event["root_sha256"] == digest(
                        context
                    )
                    if events:
                        assert (
                            event["body_position"] -
                            events[-1]["body_position"]
                            >= exp["min_branch_interval_tokens"]
                        )
                    assert event["distribution"] == out["fork"]
                    items = (
                        out["fork"]["items"][:1]
                        if arm == "reference_only"
                        else out["fork"]["items"]
                    )
                    assert len(items) == len(event["previews"])
                    for item, preview in zip(items, event["previews"]):
                        record = records[tag +
                                         f"/event-{len(events)}/candidate-{item['rank']}"]
                        assert (
                            record["request"]["root_sha256"]
                            == event["root_sha256"]
                            == preview["origin_sha256"]
                        )
                        assert record["request"]["generated_history_sha256"] == digest(
                            body)
                        assert preview == {
                            **record["result"],
                            "rank": item["rank"],
                            "probability": item["probability"],
                        }
                        assert preview["seed"] == derived_seed(
                            seed, event["root_sha256"], "candidate", item["token_id"]
                        )
                        assert record["request"]["count"] == min(
                            exp["branch_tokens"], exp["max_output_tokens"] -
                            len(body)
                        )
                        assert len(preview["ids"]
                                   ) <= record["request"]["count"]
                        assert (
                            preview["ids"][0] == item["token_id"]
                            and 1 <= len(preview["ids"]) <= exp["branch_tokens"]
                        )
                        assert not any(
                            i in model.eos_ids or i == think_end for i in preview["ids"][:-1]
                        )
                        markers = [
                            emitted_marker(model, context +
                                           preview["ids"][:i], token)
                            for i, token in enumerate(preview["ids"])
                        ]
                        assert not any(m and m.startswith("</")
                                       for m in markers[:-1])
                        assert preview["stop_marker"] == markers[-1]
                        assert preview["text"] == fragment_text(
                            model, preview["ids"])
                        assert (
                            "</think>" not in preview["text"]
                            and "</reasoning>" not in preview["text"]
                        )
                        check_guards(preview, body, forced_first=True)
                        costs.append(preview)
                    assert event["selected_rank"] == 1
                    retained = [n for n in event["previews"]
                                [1:] if n["text"].strip()]
                    if arm == "filtered_futures":
                        gate = event["similarity"]
                        record = records[tag + f"/event-{len(events)}/cosine"]
                        assert record["request"] == {
                            "root_sha256": event["root_sha256"],
                            "ranks": [n["rank"] for n in event["previews"]],
                            "texts": [n["text"] for n in event["previews"]],
                            "similarity_spec": spec["similarity"],
                        }
                        assert record["result"] == gate and gate["method"] == "embedding_cosine"
                        assert gate["threshold"] == spec["similarity"]["threshold"]
                        assert (
                            gate["texts"] == record["request"]["texts"]
                            and gate["ranks"] == record["request"]["ranks"]
                        )
                        assert gate["valid"] == [
                            bool(t.strip()) for t in gate["texts"]]
                        valid = [i for i, v in enumerate(gate["valid"]) if v]
                        dense = (
                            cosine_matrix([gate["embeddings"][i]
                                          for i in valid]) if valid else []
                        )
                        for i in range(len(gate["valid"])):
                            for j in range(len(gate["valid"])):
                                if i in valid and j in valid:
                                    assert (
                                        abs(
                                            gate["similarity_matrix"][i][j]
                                            - dense[valid.index(i)][valid.index(j)]
                                        )
                                        < 1e-10
                                    )
                                else:
                                    assert gate["similarity_matrix"][i][j] is None
                        ranks, decisions = select_distinct(
                            gate["ranks"],
                            gate["similarity_matrix"],
                            gate["valid"],
                            gate["threshold"],
                            texts=gate.get("texts"),
                        )
                        assert ranks == gate["retained_ranks"] and decisions == gate["decisions"]
                        costs.append(gate)
                        retained = [n for n in retained if n["rank"] in ranks]
                    else:
                        assert event["similarity"] is None
                    assert event["retained_ranks"] == [n["rank"]
                                                       for n in retained]
                    assert 1 not in event["retained_ranks"]
                    if retained:
                        side = model.encode(memory_text(retained))
                        assert (
                            side == event["memory_ids"]
                            and len(side) <= exp["max_event_memory_tokens"]
                        )
                        record = records[tag + f"/event-{len(events)}/inject"]
                        assert record["request"] == {
                            "root_sha256": event["root_sha256"],
                            "ids": side,
                        }
                        context.extend(side)
                        history.append(
                            {"kind": "memory", "ids": side, "event": len(events)})
                        costs.append(record["result"])
                    else:
                        assert not event["memory_ids"]
                    assert event["continuation_root_sha256"] == digest(context)
                    record = records[tag +
                                     f"/event-{len(events)}/commit-rollout"]
                    commit = record["result"]
                    assert record["request"] == {
                        "root_sha256": digest(context),
                        "ids": event["previews"][0]["ids"],
                        "selected_rank": 1,
                        "source_root_sha256": event["root_sha256"],
                        "body_position": len(body),
                        "generated_history_sha256": digest(body),
                    }
                    assert commit["ids"] == event["committed_ids"] == event["previews"][0]["ids"]
                    assert (
                        commit["cost"]["input_tokens"] == len(commit["ids"])
                        and commit["cost"]["output_tokens"] == 0
                    )
                    assert len(body) + \
                        len(commit["ids"]) <= exp["max_output_tokens"]
                    body.extend(commit["ids"])
                    context.extend(commit["ids"])
                    history.append({"kind": "body", "ids": commit["ids"]})
                    costs.append(commit)
                    assert event["after_commit_sha256"] == digest(context)
                    marker = event["previews"][0]["stop_marker"]
                    if marker and marker.startswith("</"):
                        phase = "final"
                    events.append(event)
                step += 1
            assert body == result["body_ids"] and model.decode(
                body) == result["body_text"]
            assert context and digest(
                context) == result["final_context_sha256"]
            assert (
                len(context) == result["final_context_length"]
                and len(context) <= spec["model"]["max_context_tokens"]
            )
            assert events == result["events"] and checks == result["checks"]
            assert len(compactions) == len(result["compactions"])
            assert result["body_guard_events"] == body_guards
            assert result["repetition"] == repetition_summary(
                body, exp["repetition_guard"]["max_period_tokens"]
            )
            assert result["memory_markup"] == memory_markup_summary(
                result["body_text"])
            for key, value in final_response(model, body, row, think_end).items():
                assert result[key] == value
            for key, value in sum_cost(*costs).items():
                assert abs(value - result["policy_cost"][key]) < 1e-5
            for key in ("input_tokens", "texts", "seconds"):
                assert (
                    abs(
                        result["embedding_cost"][key]
                        - sum(
                            e["similarity"]["embedding_cost"][key]
                            for e in events
                            if e["similarity"]
                        )
                    )
                    < 1e-5
                )
            completed_conditions += 1
            events_count += len(events)
            if time.monotonic() - last_log >= 15 or completed_conditions == 1:
                elapsed = time.monotonic() - started
                print(
                    f"audited {completed_conditions} conditions, {events_count} events; elapsed={elapsed:.1f}s",
                    flush=True,
                )
                last_log = time.monotonic()
        case_label = namespace + "/" + row["id"] + "/complete"
        if case_label in records:
            saved = records[case_label]["result"]
            case_path = run / "cases" / namespace / (row["id"] + ".json")
            assert json.loads(case_path.read_text(encoding="utf-8")) == saved
            case_hashes[str(case_path.relative_to(run))
                        ] = file_digest(case_path)
            for arm, c in saved["conditions"].items():
                assert records[f"{namespace}/{row['id']}/{arm}/complete"]["result"] == c
            completed_cases += 1
    if not partial:
        assert completed_cases == len(plans) and completed_conditions == len(plans) * len(
            exp["arms"]
        )
        assert json.loads(
            (run / "status.json").read_text(encoding="utf-8"))["state"] == "complete"
    return {
        "run": str(run),
        "partial": partial,
        "completed_cases": completed_cases,
        "completed_conditions": completed_conditions,
        "audit_script_sha256": file_digest(Path(__file__)),
        "events": events_count,
        "checkpoints": len(records),
        "checkpoint_sha256": hashes,
        "case_sha256": case_hashes,
        "checks": [
            "source/split/checkpoint hashes",
            "all eligible scan positions and declared candidates",
            "minimum body-token fork interval and exact scan restart boundary",
            "same pre-injection root for every candidate",
            "only unchosen alternatives in memory",
            "selected rollout committed verbatim after memory",
            "cosine matrix recomputed from vectors",
            "no intervention after thinking ends",
            "main body preserved across memory compaction",
            "generated-only repetition history and every blocked cycle token",
            "separate final-response scoring",
            "policy cost sums and replay ledgers",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run, args.partial)
    atomic_json(args.output, result)
    print(json.dumps({k: v for k, v in result.items()
          if k != "checkpoint_sha256"}, indent=2))
