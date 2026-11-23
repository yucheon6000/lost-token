# Frozen single-pass AR — whole six-benchmark suite

- aime25: 21/30
- gpqa: 275/448
- gsm8k: 1258/1319
- hmmt25: 15/30
- math500: 489/500
- mmlu: 11438/14042

Existing complete single-pass AR outcomes, unchanged model/sampler/runtime/final-answer extractor, are reused. The two disjoint historical references are united without inference, rescoring, voting or answer selection; original hashes and copies are retained in input-references/.

Frozen reference SHA256: `6ddd1f83caa9faff8fb016c4c91a04f30cbe95a192e5e775cf92c62b8d7bf7ef`. Original generation code: `changho-2026-11-15`, commit `204b01c7ee62027115be4d5456bb49acc5d382ed`. Full-cohort manifest SHA256: `fa8feb36a037f8bcb4a16a46349c36fef050dabddcc232e5406a2d4733e02c55`. Component references retain their immutable hashes/provenance in reference_derivation. Earlier scoring recovery used only saved final responses with the common terminal-box extractor; this union/publication performs no inference or rescoring.
