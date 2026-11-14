# Lost Tokens 공용 평가 허브

이 브랜치 **`shared-evaluation`**에는 가이드·고정 서브셋·모든 사람의 실험 결과를 모읍니다.
개인 구현 코드와 설정은 각 **`{name}-{YYYY-MM-DD}`** 브랜치에서 관리합니다.

- **[전체 실험 비교표](experiment-results/README.md)** / [비교 CSV](experiment-results/comparison.csv)
- **[Claude 진입 문서](CLAUDE.md)** / [공통 실험 가이드](docs/EXPERIMENT_GUIDE.md)
- **[공통 고정 subset](evaluation/subsets/shared-v1/manifest.json)**
- [Changho pilot 결과](experiment-results/changho-2026-11-15/summary.md)
- [실행 코드·설정 브랜치](https://github.com/yucheon6000/lost-token/tree/changho-2026-11-15)

| 개인 브랜치 | 이 공용 브랜치 |
|---|---|
| src, tests, configs, 실행 스크립트, 의존성/lock | guide, 고정 ID/manifest, baseline/ours/방법/환경/작은 결과물 |
| 코드 commit/push | 결과 제출 commit/push + 통합 비교표 갱신 |

결과 제출은 `experiment-results/{name}-{date}/`에 추가합니다. 기존 제출을 덮어쓰지 않습니다.
동일한 cohort·모델·backend·seed·정밀도·채점 조건끼리 비교하도록 표를 자동 생성합니다.
과거 5% pilot과 새 공통 평가셋은 서로 다른 그룹으로 표시합니다.

공통 평가: AIME/HMMT/GSM8K 전체, GPQA 448개 전체, MATH500 250개(50%), MMLU 3,511개(25%, 올림).
문제 ID를 각자 재추첨하지 않습니다. 실제 모델/데이터/환경/대규모 checkpoint는 업로드하지 않습니다.

`source-snapshot/`, `run-reports/*/provenance/`의 코드는 과거 결과를 검증하는 동결 증거입니다.
이 허브에서 개발하거나 학습하는 구현 코드가 아닙니다.
