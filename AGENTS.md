# Shared evaluation hub

- Read CLAUDE.md and docs/EXPERIMENT_GUIDE.md first.
- This branch stores canonical guides, immutable subset IDs and collected results only.
- Develop code/settings/tests on personal {name}-{YYYY-MM-DD} branches; never merge their entire code tree here.
- Submit results under experiment-results/{name}-{date}/, including baseline.md, ours.md, method.md, environment.json and submission.json.
- Validate the submission and regenerate experiment-results/README.md and comparison.csv with tools/results.py.
- Group comparisons by cohort/model/backend/seed/precision/scorer identity. Never fabricate an unmeasured baseline.
- Never replace others' submissions or redraw canonical subsets. Existing source snapshots are immutable historical evidence.
- Push results to shared-evaluation normally; no force-push and no direct main push. Rebase/regenerate the index on concurrent submissions.
- Tools here use Python stdlib only; do not install packages into system Python or launch GPU experiments from this hub.
