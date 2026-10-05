"""Threshold-triggered memory throughout a thinking trace, with no event-count cap.

Each condition owns its continuing cache. Only speculative rollouts clone it.
Durable calls store generated tokens and replay the original forward shapes on
resume; per-position sampling seeds avoid changing randomness at checkpoint cuts.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import random
import re
import time

from .core import derived_seed, digest, sum_cost
from .math_scoring import natural_answer
from .math_scoring import math_correct
from .cosine import compare_rollouts
from .repetition import repeated_suffix, repetition_summary, memory_markup_summary


ARMS = ("plain_ar", "reference_only", "all_futures", "filtered_futures")
REASONING_MARKERS = re.compile(r"</?(?:think|reasoning)>")


def raw_text(model, ids):
    return model.tokenizer.decode(ids, skip_special_tokens=False)


def reasoning_phase(model, ids):
    markers = list(REASONING_MARKERS.finditer(raw_text(model, ids)))
    if not markers:
        return "waiting"
    return "final" if markers[-1].group().startswith("</") else "thinking"


def emitted_marker(model, before, token):
    """Recognize complete markers, including multi-token </reasoning>, on emission."""
    tail = before[-32:]
    old = raw_text(model, tail)
    new = raw_text(model, tail + [token])
    matches = [m for m in REASONING_MARKERS.finditer(new) if m.end() > len(old)]
    return matches[0].group() if matches else None


def fragment_text(model, ids):
    text = model.decode(ids)
    for marker in ("</think>", "</reasoning>"):
        text = text.split(marker, 1)[0]
    return text


def instruction(row):
    ending = (
        "Please reason step by step, and put your final answer within \\boxed{}."
        if row.get("answer_format") == "math"
        else "Please reason step by step. End your final response with 'Final answer: (LETTER)'."
    )
    return ending + "\n\nProblem:\n"


def final_response(model, body, row, think_end_id):
    """Separate answer accuracy from thinking-format validity; never parse a capped open scratchpad."""
    raw = raw_text(model, body)
    endings = list(re.finditer(r"</(?:think|reasoning)>", raw))
    closed = bool(endings)
    eos = bool(body and body[-1] in model.eos_ids)
    if not closed and not eos:
        return {
            "thinking_complete": False,
            "thinking_tokens": len(body),
            "answer_tokens": 0,
            "answer_text": "",
            "prediction": None,
            "correct": False,
            "answer_source": "open_thinking_at_cap",
        }
    native = closed and endings[0].group() == "</think>" and think_end_id in body
    boundary = body.index(think_end_id) if native else -1
    if native:
        answer = model.decode(body[boundary + 1 :])
    elif closed:
        visible = model.decode(body)
        match = re.search(r"</(?:think|reasoning)>", visible)
        answer = visible[match.end() :] if match else ""
    else:
        answer = model.decode(body)
    prediction = natural_answer(answer, row)
    correct = (
        (
            math_correct(row["gold"], prediction)
            if row.get("answer_format") == "math"
            else prediction == row["gold"]
        )
        if prediction is not None
        else False
    )
    return {
        "thinking_complete": closed,
        "thinking_tokens": boundary + 1 if native else None,
        "answer_tokens": len(body) - boundary - 1 if native else None,
        "answer_text": answer,
        "answer_source": "after_thinking_end" if closed else "eos_without_thinking_end",
        "prediction": prediction,
        "correct": bool(correct),
    }


@dataclass
class StreamState:
    """Exclusively owned, consumed by advance(); never passed to a sibling directly."""

    ids: list[int]
    cache: object
    logits: object
    generated_ids: list[int] = field(default_factory=list)


class StreamDecoder:
    def __init__(self, model, exp):
        self.model, self.torch, self.exp = model, model.torch, exp
        self.think_end = model.encode("</think>")
        if len(self.think_end) != 1:
            raise ValueError("Require a single-token thinking boundary")
        self.think_end = self.think_end[0]

    def prefill(self, ids):
        self.model._check(ids)
        cache, logits = None, None
        started = last_log = time.monotonic()
        with self.torch.inference_mode():
            for start in range(0, len(ids), self.exp["prefill_chunk_tokens"]):
                out = self.model.model(
                    input_ids=self.torch.tensor(
                        [ids[start : start + self.exp["prefill_chunk_tokens"]]],
                        device=self.model.device,
                    ),
                    past_key_values=cache,
                    use_cache=True,
                    logits_to_keep=1,
                )
                cache, logits = out.past_key_values, out.logits[0, -1].float()
                if time.monotonic() - last_log >= 15:
                    done = min(start + self.exp["prefill_chunk_tokens"], len(ids))
                    elapsed = time.monotonic() - started
                    self.model.log(
                        f"prefill {done}/{len(ids)} tokens; elapsed={elapsed:.1f}s ETA={elapsed / done * (len(ids) - done):.1f}s"
                    )
                    last_log = time.monotonic()
        return StreamState(list(ids), cache, logits)

    def advance(self, state, ids, block_size=1, generated=False):
        self.model._check(state.ids, len(ids))
        with self.torch.inference_mode():
            for start in range(0, len(ids), block_size):
                part = ids[start : start + block_size]
                out = self.model.model(
                    input_ids=self.torch.tensor([part], device=self.model.device),
                    past_key_values=state.cache,
                    use_cache=True,
                    logits_to_keep=1,
                )
                state.cache, state.logits = out.past_key_values, out.logits[0, -1].float()
                state.ids.extend(part)
                if generated:
                    state.generated_ids.extend(part)
        return state

    def candidates(self, state):
        # A probability threshold itself bounds the number of qualifying tokens;
        # there is no top-2 truncation, lexical filter, ratio gate, or cooldown.
        lp = state.logits.log_softmax(-1)
        count = min(len(lp), int(1 / self.exp["min_candidate_probability"]) + 1)
        values, indices = self.torch.topk(lp, count)
        observations = list(zip(indices.tolist(), values.exp().tolist()))
        items = [
            {
                "rank": rank + 1,
                "token_id": token,
                "text": self.model.decode([token]),
                "probability": prob,
            }
            for rank, (token, prob) in enumerate(observations)
            if prob >= self.exp["min_candidate_probability"] and token not in self.model.special_ids
        ]
        top_special = observations[0][0] in self.model.special_ids
        eligible = not top_special and len(items) >= 2
        return {
            "eligible": eligible,
            "items": items if eligible else [],
            "top_token_id": observations[0][0],
            "top_probability": observations[0][1],
            "second_probability": observations[1][1],
            "top_is_special": top_special,
            "entropy": float(-(lp.exp() * lp).sum()),
        }

    def sample(self, state, seed):
        logits = state.logits / self.exp["temperature"]
        guard = self.loop_guard(state)
        if guard is not None:
            logits = logits.clone()
            logits[guard["blocked_token"]] = -self.torch.inf
        values, indices = self.torch.topk(logits, min(self.exp["top_k"], len(state.logits)))
        probabilities = values.softmax(-1)
        probabilities = probabilities.masked_fill(
            probabilities.cumsum(-1) - probabilities > self.exp["top_p"], 0
        )
        generator = self.torch.Generator(device=self.model.device).manual_seed(seed)
        index = self.torch.multinomial(probabilities, 1, generator=generator)
        token = int(indices[index].item())
        return token, float(state.logits.log_softmax(-1)[token])

    def loop_guard(self, state):
        guard = repeated_suffix(state.generated_ids, self.exp["repetition_guard"])
        # Never prevent termination; the guard applies only to ordinary continuation.
        if guard and guard["blocked_token"] in self.model.eos_ids | {self.think_end}:
            return None
        return guard

    @staticmethod
    def cost(start, count, generated, seconds=0.0):
        return {
            "input_tokens": count - generated,
            "output_tokens": generated,
            "forward_tokens": count,
            "attention_pairs": count * start + count * (count + 1) // 2,
            "seconds": seconds,
        }

    def segment(self, state, count, seed, body_position, scan):
        start_length = len(state.ids)
        started = last_log = time.monotonic()
        ids, logprobs, checks, guard_events = [], [], [], []
        fork = None
        stop_marker = None
        for offset in range(count):
            if scan:
                dist = self.candidates(state)
                checks.append({"body_position": body_position + offset, **dist})
                if dist["eligible"]:
                    fork = dist
                    break
            guard = self.loop_guard(state)
            token, lp = self.sample(state, derived_seed(seed, "body", body_position + offset))
            if guard:
                guard_events.append({"offset": offset, "sampled_token": token, **guard})
            stop_marker = emitted_marker(self.model, state.ids, token)
            self.advance(state, [token], generated=True)
            ids.append(token)
            logprobs.append(lp)
            if token in self.model.eos_ids or stop_marker is not None:
                break
            if time.monotonic() - last_log >= 15:
                elapsed = time.monotonic() - started
                self.model.log(
                    f"body chunk {len(ids)}/{count}; elapsed={elapsed:.1f}s ETA(cap)={elapsed / len(ids) * (count - len(ids)):.1f}s"
                )
                last_log = time.monotonic()
        self.model._sync()
        return {
            "ids": ids,
            "raw_log_probabilities": logprobs,
            "checks": checks,
            "fork": fork,
            "stop_marker": stop_marker,
            "guard_events": guard_events,
            "cost": self.cost(start_length, len(ids), len(ids), time.monotonic() - started),
        }

    def rollout(self, root, first, seed, count=None):
        started = time.monotonic()
        count = self.exp["branch_tokens"] if count is None else count
        if not 1 <= count <= self.exp["branch_tokens"]:
            raise ValueError("Invalid rollout length")
        # Both layer objects AND their tensors are copied. A generated sibling
        # cannot mutate root, and its returned cache is never the continuing cache.
        state = StreamState(
            list(root.ids), copy.deepcopy(root.cache), root.logits.clone(), list(root.generated_ids)
        )
        ids, logprobs, guard_events = [], [], []
        stop_marker = None
        for index in range(count):
            if index == 0:
                token = first
                lp = float(state.logits.log_softmax(-1)[token])
            else:
                guard = self.loop_guard(state)
                token, lp = self.sample(state, derived_seed(seed, "rollout", index))
                if guard:
                    guard_events.append({"offset": index, "sampled_token": token, **guard})
            stop_marker = emitted_marker(self.model, state.ids, token)
            self.advance(state, [token], generated=True)
            ids.append(token)
            logprobs.append(lp)
            if token in self.model.eos_ids or (stop_marker and stop_marker.startswith("</")):
                break
            if index >= 12:
                tok_str = self.model.decode([token])
                if any(c in tok_str for c in (".\n", ".\n\n", ".\t", ". ", "\n\n", "\n-", "\n*")):
                    break
        self.model._sync()
        return {
            "ids": ids,
            "text": fragment_text(self.model, ids),
            "first_token": first,
            "seed": seed,
            "stop_marker": stop_marker,
            "guard_events": guard_events,
            "origin_sha256": digest(root.ids),
            "raw_log_probabilities": logprobs,
            "cost": self.cost(len(root.ids), len(ids), len(ids), time.monotonic() - started),
        }


def compact_history(history, target):
    """Drop oldest side blocks only, retaining every generated body token in order."""
    remaining = sum(len(h["ids"]) for h in history if h["kind"] == "memory")
    kept, removed = [], []
    for block in history:
        if block["kind"] == "memory" and remaining > target:
            remaining -= len(block["ids"])
            removed.append(block["event"])
        else:
            kept.append(block)
    return kept, removed


def memory_text(notes):
    """Structured Contrastive Hypotheses framing inside possibilities block."""

    def escape(text):
        return re.sub(
            r"</?(?:possibilities|contrastive_hypotheses|think|reasoning)>",
            lambda m: m.group().replace("<", "&lt;").replace(">", "&gt;"),
            text,
            flags=re.I,
        )

    formatted = []
    for i, n in enumerate(notes):
        clean_text = escape(n["text"]).strip()
        formatted.append(f"- Alternative Path [{i+1}]: {clean_text}")

    return (
        "\n<possibilities>\n"
        + "\n".join(formatted)
        + "\n</possibilities>\n"
    )


def run_condition(model, store, row, cfg, namespace, arm, log):
    exp = cfg["experiment"]
    decoder = StreamDecoder(model, exp)
    seed = derived_seed(exp["seed"], namespace, row["id"])
    tag = f"{namespace}/{row['id']}/{arm}"
    base = model.prompt(instruction(row) + row["question"])
    state = decoder.prefill(base)
    prefill = store.call(
        tag + "/prefill", {"ids": base}, lambda: {"cost": decoder.cost(0, len(base), 0)}
    )
    body, history, events, checks, costs, compactions, body_guards = (
        [],
        [],
        [],
        [],
        [prefill],
        [],
        [],
    )
    step = 0
    phase = reasoning_phase(model, base)
    has_reasoning_token = False
    started = last_log = time.monotonic()
    recovery_seconds = 0.0

    def persisted_segment(label, count, scan):
        nonlocal recovery_seconds
        position = len(body)
        request = {
            "root_sha256": digest(state.ids),
            "root_length": len(state.ids),
            "generated_history_sha256": digest(state.generated_ids),
            "body_position": position,
            "count": count,
            "seed": seed,
            "scan": scan,
        }
        fresh_state = False

        def fresh():
            nonlocal fresh_state
            fresh_state = True
            return decoder.segment(state, count, seed, position, scan)

        result = store.call(tag + "/" + label, request, fresh)
        if not fresh_state:
            recovery_start = time.monotonic()
            decoder.advance(state, result["ids"], generated=True)
            recovery_seconds += time.monotonic() - recovery_start
        if result["ids"]:
            body.extend(result["ids"])
            history.append({"kind": "body", "ids": result["ids"]})
        checks.extend(result["checks"])
        costs.append(result)
        body_guards.extend(
            {"body_position": position + g["offset"], **g} for g in result["guard_events"]
        )
        return result

    while len(body) < exp["max_output_tokens"] and (not body or body[-1] not in model.eos_ids):
        # Compaction happens BEFORE a new fork is considered. Rollout parents and
        # the injection parent thus remain exactly the same root for every event.
        memory_tokens = sum(len(h["ids"]) for h in history if h["kind"] == "memory")
        if memory_tokens > exp["memory_capacity_tokens"] - exp["max_event_memory_tokens"]:
            old_digest = digest(state.ids)
            history, removed = compact_history(history, exp["memory_compact_to_tokens"])
            context = base + [token for block in history for token in block["ids"]]
            del state
            rebuild_started = time.monotonic()
            state = decoder.prefill(context)
            state.generated_ids = list(body)
            result = store.call(
                tag + f"/step-{step}/compact",
                {
                    "before_sha256": old_digest,
                    "removed_events": removed,
                    "after_sha256": digest(context),
                },
                lambda: {
                    "removed_events": removed,
                    "body_tokens_preserved": len(body),
                    "cost": decoder.cost(0, len(context), 0, time.monotonic() - rebuild_started),
                },
            )
            costs.append(result)
            compactions.append(
                {**result, "body_position": len(body), "remaining_context_length": len(context)}
            )
        count = min(exp["checkpoint_body_tokens"], exp["max_output_tokens"] - len(body))
        if phase == "thinking" and not has_reasoning_token:
            count = 1
        scan = phase == "thinking" and has_reasoning_token and arm != "plain_ar"
        next_fork_position = (
            (events[-1]["body_position"] + exp["min_branch_interval_tokens"]) if events else 0
        )
        if scan and len(body) < next_fork_position:
            # Count only body tokens, including the committed rollout. Side input
            # length and compaction never advance this clock. Resume checks at the
            # exact boundary instead of skipping the rest of a checkpoint chunk.
            count = min(count, next_fork_position - len(body))
            scan = False
        segment = persisted_segment(f"step-{step}/scan", count, scan)
        marker = segment["stop_marker"]
        if marker and marker.startswith("</"):
            phase = "final"
        elif marker and phase == "waiting":
            phase = "thinking"
            has_reasoning_token = False
        elif phase == "thinking" and segment["ids"]:
            has_reasoning_token = True
        dist = segment["fork"]
        if dist is not None:
            event_index = len(events)
            root_sha = digest(state.ids)
            event = {
                "index": event_index,
                "body_position": len(body),
                "root_sha256": root_sha,
                "root_length": len(state.ids),
                "distribution": dist,
                "previews": [],
                "similarity": None,
                "selected_rank": 1,
                "retained_ranks": [],
                "memory_ids": [],
            }
            candidates = dist["items"] if arm != "reference_only" else dist["items"][:1]
            rollout_count = min(exp["branch_tokens"], exp["max_output_tokens"] - len(body))
            for item in candidates:
                branch_seed = derived_seed(seed, root_sha, "candidate", item["token_id"])
                request = {
                    "root_sha256": root_sha,
                    "root_length": len(state.ids),
                    "first_token": item["token_id"],
                    "seed": branch_seed,
                    "count": rollout_count,
                }
                request["generated_history_sha256"] = digest(state.generated_ids)
                preview = store.call(
                    tag + f"/event-{event_index}/candidate-{item['rank']}",
                    request,
                    lambda item=item, branch_seed=branch_seed: decoder.rollout(
                        state, item["token_id"], branch_seed, rollout_count
                    ),
                )
                preview = {**preview, "rank": item["rank"], "probability": item["probability"]}
                event["previews"].append(preview)
                costs.append(preview)
            retained = [n for n in event["previews"][1:] if n["text"].strip()]
            if arm == "filtered_futures":
                similarity_spec = cfg["similarity"]
                request = {
                    "root_sha256": root_sha,
                    "ranks": [n["rank"] for n in event["previews"]],
                    "texts": [n["text"] for n in event["previews"]],
                    "similarity_spec": similarity_spec,
                }
                result = store.call(
                    tag + f"/event-{event_index}/cosine",
                    request,
                    lambda: compare_rollouts(
                        model.semantic_encoder, event["previews"], similarity_spec["threshold"]
                    ),
                )
                event["similarity"] = result
                costs.append(result)
                retained = [n for n in retained if n["rank"] in result["retained_ranks"]]
            if retained:
                text = memory_text(retained)
                side = model.encode(text)
                if len(side) > exp["max_event_memory_tokens"]:
                    raise ValueError(
                        "Memory reservation too small; refusing to silently drop qualifying candidates"
                    )
                event["retained_ranks"] = [n["rank"] for n in retained]
                event["memory_ids"] = side
                event["memory_text"] = text
                before = len(state.ids)
                ingest_started = time.monotonic()
                decoder.advance(state, side, exp["prefill_chunk_tokens"])
                ingestion = store.call(
                    tag + f"/event-{event_index}/inject",
                    {"root_sha256": root_sha, "ids": side},
                    lambda: {
                        "cost": decoder.cost(
                            before, len(side), 0, time.monotonic() - ingest_started
                        )
                    },
                )
                costs.append(ingestion)
                history.append({"kind": "memory", "ids": side, "event": event_index})
            event["continuation_root_sha256"] = digest(state.ids)
            chosen = event["previews"][0]["ids"]
            # The selected rollout becomes body text verbatim AFTER the alternatives.
            # Its branch KV cannot be reused because the continuing KV includes memory.
            commit_request = {
                "root_sha256": digest(state.ids),
                "ids": chosen,
                "selected_rank": 1,
                "generated_history_sha256": digest(state.generated_ids),
                "source_root_sha256": root_sha,
                "body_position": len(body),
            }
            advanced = False

            def commit():
                nonlocal advanced
                before = len(state.ids)
                commit_started = time.monotonic()
                decoder.advance(state, chosen, generated=True)
                advanced = True
                return {
                    "ids": chosen,
                    "cost": decoder.cost(before, len(chosen), 0, time.monotonic() - commit_started),
                }

            committed = store.call(
                tag + f"/event-{event_index}/commit-rollout", commit_request, commit
            )
            if not advanced:
                recovery_start = time.monotonic()
                decoder.advance(state, committed["ids"], generated=True)
                recovery_seconds += time.monotonic() - recovery_start
            body.extend(committed["ids"])
            history.append({"kind": "body", "ids": committed["ids"]})
            costs.append(committed)
            event["committed_ids"] = committed["ids"]
            event["after_commit_sha256"] = digest(state.ids)
            if event["previews"][0]["stop_marker"] and event["previews"][0][
                "stop_marker"
            ].startswith("</"):
                phase = "final"
            store.call(
                tag + f"/event-{event_index}/complete",
                {"body_position": event["body_position"], "root_sha256": root_sha},
                lambda: event,
            )
            events.append(event)
        step += 1
        if time.monotonic() - last_log >= 15 or step == 1:
            elapsed = time.monotonic() - started
            eta = f"{elapsed / max(1, len(body)) * (exp['max_output_tokens'] - len(body)):.1f}s"
            log(
                f"{row['id']} {arm}: body={len(body)}/{exp['max_output_tokens']}; events={len(events)}; "
                f"injections={sum(bool(e['memory_ids']) for e in events)}; context={len(state.ids)}; elapsed={elapsed:.1f}s ETA(cap)={eta}"
            )
            last_log = time.monotonic()
    return {
        "arm": arm,
        "body_ids": body,
        "body_text": model.decode(body),
        "events": events,
        "checks": checks,
        "ended": bool(body and body[-1] in model.eos_ids),
        "body_budget": exp["max_output_tokens"],
        "final_context_sha256": digest(state.ids),
        "final_context_length": len(state.ids),
        "retained_memory_events": [h["event"] for h in history if h["kind"] == "memory"],
        "compactions": compactions,
        "body_guard_events": body_guards,
        "repetition": repetition_summary(body, exp["repetition_guard"]["max_period_tokens"]),
        "memory_markup": memory_markup_summary(model.decode(body)),
        "embedding_cost": {
            k: sum(e["similarity"]["embedding_cost"][k] for e in events if e["similarity"])
            for k in ("input_tokens", "texts", "seconds")
        },
        "policy_cost": sum_cost(*costs),
        "recovery_seconds": recovery_seconds,
        **final_response(model, body, row, decoder.think_end),
    }


def run_case(model, store, row, cfg, namespace, log):
    order = list(cfg["experiment"]["arms"])
    random.Random(derived_seed(cfg["experiment"]["seed"], row["id"], "arm-order")).shuffle(order)
    conditions = {}
    for arm in order:
        log(f"condition start {namespace}/{row['id']}/{arm}")
        conditions[arm] = store.call(
            f"{namespace}/{row['id']}/{arm}/complete",
            {"row_id": row["id"], "arm": arm},
            lambda arm=arm: run_condition(model, store, row, cfg, namespace, arm, log),
        )
    return {**row, "namespace": namespace, "arm_order": order, "conditions": conditions}
