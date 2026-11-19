# Entropy-guided arithmetic re-sampling

Code commit `35d6be57afb12fe610a05a9febb8a300f6799f46`. Cohort `l40s-2h-v1` with manifest hash `6fdcd29e0148339bb2e7541099ad69b93f5bb8e79f3e8ce5885bd222a88ed0ba`.

Blended-memory Ours resamples from the value boundary of the highest-entropy closed, inconsistent numeric equality in the chosen preview. Each question can trigger up to one probe of eight deterministically seeded continuations. A replacement requires a complete right-hand value that passes exact arithmetic.

Each task used one L40S with the canonical per-GPU batch size, and other tasks started when additional GPUs had enough idle capacity. Some launches shared GPU memory with idle CUDA contexts, recorded per task in environment.json. Full config and runtime details are in [study-plan.json](study-plan.json) and [environment.json](environment.json).
