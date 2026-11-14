# Shared evaluation hub

- Read CLAUDE.md, docs/EXPERIMENT_GUIDE.md and docs/EVALUATION_PROFILES.md first.
- All participants MUST use the exact registered IDs: l40s-4gpu -> l40s-2h-v1 (4 L40S; AIME/HMMT batch 4, others 8); pro6000-8gpu -> unchanged shared-v1 (8 RTX PRO 6000 Blackwell; batch 8). Never redraw subsets or mix the two result groups.
- This branch stores canonical guides, immutable subset IDs and collected results only.
- Each person measures and freezes their own full AR baseline once per comparison family. Subsequent variants MUST use --arms ours --baseline-ref; keep the reference hash, original commit and paired comparisons. A new person first measures their own baseline. See docs/BASELINE_REUSE.md.
- Develop code/settings/tests on personal {name}-{YYYY-MM-DD} branches; never merge their entire code tree here.
- Submit results under experiment-results/{name}-{date}/, including baseline.md, ours.md, method.md, environment.json and submission.json.
- Validate the submission and regenerate experiment-results/README.md and comparison.csv with tools/results.py.
- Group comparisons by cohort/model/backend/seed/precision/scorer identity. Never fabricate an unmeasured baseline.
- Never replace others' submissions or redraw canonical subsets. Existing source snapshots are immutable historical evidence.
- Push results to shared-evaluation normally; no force-push and no direct main push. Rebase/regenerate the index on concurrent submissions.
- Tools here use Python stdlib only; do not install packages into system Python or launch GPU experiments from this hub.
