# Lost Tokens: 개인 코드 브랜치

이 브랜치는 `{name}-{YYYY-MM-DD}` 형식의 **코드·설정·테스트 전용** 브랜치다.
공용 가이드, 고정 평가 ID, 결과 모음의 정본은 **`shared-evaluation` 브랜치**다.

먼저 `AGENTS.md`와 아래 정본 가이드를 읽는다.

- [하드웨어별 필수 고정 IDs/프로필](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/docs/EVALUATION_PROFILES.md)
- [작업자별 baseline 1회 동결 → ours-only 반복](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/docs/BASELINE_REUSE.md)
- [공용 가이드](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/docs/EXPERIMENT_GUIDE.md)
- [모든 실험 비교표](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/experiment-results/README.md)

공용 checkout이 없으면 다음처럼 별도 worktree를 만든다. 기존 checkout/변경은 덮어쓰지 않는다.

```bash
git fetch origin shared-evaluation
git worktree add --detach .shared-evaluation origin/shared-evaluation
```

`.shared-evaluation/docs/EXPERIMENT_GUIDE.md`를 읽고 진행한다. 공용 checkout 경로가 다르면
`scripts/shared_eval.py --shared-root /path/to/shared-checkout`으로 지정한다.
가이드나 고정 ID를 개인 브랜치에 복제/재추첨하지 않는다.

`shared_eval.py`는 결과를 `workspace/shared-studies/{name}-{date}/submission/`에 만든다.
개인 브랜치에는 결과를 commit하지 않는다. 결과의 baseline.md / ours.md / method.md /
environment.json / submission.json을 공용 checkout의 `experiment-results/{name}-{date}/`로
옮기고, 공용 비교표를 갱신한 뒤 `shared-evaluation`으로 push한다.
코드 commit과 결과 commit을 분리하고 공용 브랜치에 개인 코드를 merge하지 않는다.

사용자가 문서·상태·분석만 요청한 경우 GPU 실험을 임의로 시작하지 않는다.
실험 중 source/config/runtime을 변경하거나 타인의 GPU 프로세스를 종료하지 않는다.

하드웨어 프로필을 명시한다: L40S 4장 `--profile l40s-4gpu`, PRO 6000 Blackwell 8장 `--profile pro6000-8gpu`.
L40S AIME/HMMT의 batch=4는 wrapper가 자동 적용한다. 두 cohort의 결과는 섞지 않는다.
첫 `run --arms baseline`을 전체 ID에서 완료/audit하면 `submission/baseline-reference.json`이 동결된다.
새 방법은 새 개인 브랜치에서 `run --arms ours --baseline-ref <본인의 동결 reference>`로 실행한다.
같은 reference를 유지하고 새 baseline worker를 반복 실행하지 않는다. 다음 작업자도 본인 baseline을 먼저 측정한다.
