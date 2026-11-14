# Lost Tokens 공용 평가 허브

이 브랜치 **`shared-evaluation`**에는 가이드·고정 서브셋·모든 사람의 실험 결과를 모읍니다.
개인 구현 코드와 설정은 각 **`{name}-{YYYY-MM-DD}`** 브랜치에서 관리합니다.

- **[작업자별 baseline 1회 동결 → ours-only 반복 평가](docs/BASELINE_REUSE.md)**
- **[전체 실험 비교표](experiment-results/README.md)** / [비교 CSV](experiment-results/comparison.csv)
- **[Claude 진입 문서](CLAUDE.md)** / [공통 실험 가이드](docs/EXPERIMENT_GUIDE.md)
- **[하드웨어별 필수 고정 서브셋·실행법](docs/EVALUATION_PROFILES.md)** / [프로필 정본](evaluation/profiles.json)
- [L40S 4 GPU 고정 IDs](evaluation/subsets/l40s-2h-v1/manifest.json) / [PRO 6000 8 GPU 고정 IDs](evaluation/subsets/shared-v1/manifest.json)
- [Changho pilot 결과](experiment-results/changho-2026-11-15/summary.md)
- [두 프로필을 지원하는 실행 코드 브랜치](https://github.com/yucheon6000/lost-token/tree/ch-2026-11-15)

| 개인 브랜치 | 이 공용 브랜치 |
|---|---|
| src, tests, configs, 실행 스크립트, 의존성/lock | guide, 고정 ID/manifest, baseline/ours/방법/환경/작은 결과물 |
| 코드 commit/push | 결과 제출 commit/push + 통합 비교표 갱신 |

결과 제출은 `experiment-results/{name}-{date}/`에 추가합니다. 기존 제출을 덮어쓰지 않습니다.
동일한 cohort·모델·backend·seed·정밀도·채점 조건끼리 비교하도록 표를 자동 생성합니다.
과거 5% pilot과 새 공통 평가셋은 서로 다른 그룹으로 표시합니다.

**같은 프로필을 사용하는 모든 사람은 아래 정본 ID 파일을 그대로 사용합니다. 비율만 맞춘 재추첨·각자 만든 subset·`--limit` 대체는 금지합니다.**

| 실행 프로필 | GPU | 고정 cohort | AIME / HMMT / GSM8K / GPQA / MATH500 / MMLU |
|---|---|---|---|
| `l40s-4gpu` | L40S **4장** | [`l40s-2h-v1`](evaluation/subsets/l40s-2h-v1/) | **30 / 25 / 1,319 / 90 / 125 / 550** |
| `pro6000-8gpu` | RTX PRO 6000 Blackwell **8장** | [`shared-v1`](evaluation/subsets/shared-v1/) | **30 / 30 / 1,319 / 448 / 250 / 3,511** |

L40S는 데이터셋별 **baseline+ours 합계 약 2시간**을 목표로 실측 속도에서 산정했습니다.
AIME/HMMT는 GPU당 batch **4**, 나머지는 **8**입니다. 시간은 추정이며 엄격한 상한 보장은 아닙니다.
PRO 6000의 기존 ID/manifest는 그대로 보존하며 2시간 제한을 적용하지 않습니다.
두 cohort 및 하드웨어의 결과·시간은 별도 그룹으로 보고합니다. [필수 실행 명령과 주의점](docs/EVALUATION_PROFILES.md)을 먼저 읽으세요.
모델/원본 데이터/환경/대규모 checkpoint는 업로드하지 않습니다.

`source-snapshot/`, `run-reports/*/provenance/`의 코드는 과거 결과를 검증하는 동결 증거입니다.
이 허브에서 개발하거나 학습하는 구현 코드가 아닙니다.
