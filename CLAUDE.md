# Lost Tokens: 개인 코드 브랜치

이 브랜치는 `{name}-{YYYY-MM-DD}` 형식의 **코드·설정·테스트 전용** 브랜치다.
공용 가이드, 고정 평가 ID, 결과 모음의 정본은 **`shared-evaluation` 브랜치**다.

먼저 `AGENTS.md`와 아래 정본 가이드를 읽는다.

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
