# Incorrect answers

| Run | Incorrect / total |
|---|---:|
| aime25-main-baseline-8gpu | 6 / 30 |
| aime25-main-ours-8gpu | 5 / 30 |
| gpqa-main-baseline-8gpu | 200 / 448 |
| gpqa-main-ours-8gpu | 203 / 448 |
| hmmt25-main-baseline-8gpu | 12 / 30 |
| hmmt25-main-ours-8gpu | 16 / 30 |
| math500-main-baseline-8gpu | 15 / 500 |
| math500-main-ours-8gpu | 13 / 500 |

Each run folder contains one readable Markdown file per incorrect case and failures.jsonl with the question, expected/model answers, full trace and branch events. index.csv covers all failures.

These are observed traces and scoring outcomes, not a verified diagnosis of why the model failed. Original experiment records are unchanged.
