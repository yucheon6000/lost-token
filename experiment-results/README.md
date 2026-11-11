# Experiment results

- `summaries/baseline-results.md`: accuracy and runtime comparisons.
- `run-logs/`: controller, worker and validation logs.
- `run-reports/`: reports, run settings, frozen source, identities, audits and case outcomes.
- `incorrect-answers/`: 470 readable error cases and a CSV index.

Large JSONL exports are gzip-compressed in ordered chunks. Individual Markdown cases are directly readable. Restore a run’s JSONL from its directory with:

```bash
gzip -cd failures-*.jsonl.gz > failures.jsonl
```

Chunks must be concatenated in filename order; an individual chunk can end inside a JSON record. `compressed-files.json` records the original SHA256 and ordered parts. All compressed exports were verified byte-for-byte after restoration.

This is a snapshot of the local experiment artifacts. Raw inference checkpoints, models, environments and downloaded datasets remain outside Git. Run logs include earlier interrupted attempts; final `status.json` files identify completed, audited runs.
