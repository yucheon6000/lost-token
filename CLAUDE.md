# Lost Tokens: Claude 작업 진입점

먼저 [AGENTS.md](AGENTS.md)와 [공통 실험 가이드](docs/EXPERIMENT_GUIDE.md)를 읽는다.
실험 요청이면 가이드의 실행/재개/보고/push 절차를 끝까지 수행한다.
사용자가 문서 작성·분석·상태 확인만 요청한 경우 GPU 실험을 임의로 시작하지 않는다.

- 공통 평가 문제는 `evaluation/subsets/shared-v1/manifest.json`과 인접 ID JSON이 기준이다.
- GPQA 전체 448개, MATH500 250개, MMLU 3,511개. AIME25/HMMT25/GSM8K는 전체셋.
- 개인별 재추첨, `--limit` 대체, 5% 파일 재사용, 임의의 dataset revision 변경을 금지한다.
- 브랜치 이름은 `{name}-{YYYY-MM-DD}`. 사용자가 지정한 이름/날짜를 우선한다.
- 결과는 `experiment-results/{name}-{date}/baseline.md`, `ours.md`, `method.md`에 **모두** 작성한다.
- 환경은 `environment.json`에 기록한다. GPU 모델/장수/번호, driver/CUDA, 패키지 버전,
  정밀도와 배치/worker 수를 저장하고 결과 문서에서 연결한다.
- `baseline`은 일반 AR(`plain_ar`)이다. lookahead를 baseline으로 이름 바꾸지 않는다.
- GPU 사용 전 타 작업 확인. 실행 중 소스/설정 변경 금지. 체크포인트 identity 검사를 우회하지 않는다.
- 설치는 `uv sync --frozen`, 실행은 `uv run --frozen`. 독립 환경을 유지한다.
- 승인된 push 요청이면 검증 후 해당 개인 브랜치로 push한다. main에 직접 push하거나 force-push하지 않는다.

권장 사용자 프롬프트:

> CLAUDE.md와 공통 실험 가이드를 읽고, 이름은 MYNAME으로 진행해.
> 방법은 [구체적인 변경 내용]이고 가설은 [검증하려는 가설]이야.
> 공통 고정셋에서 baseline/ours를 같은 조건으로 평가하고 결과/방법 문서를 정리해.
> 사용 가능한 GPU는 [GPU 목록]이며, 검증 후 내 {name}-{date} 브랜치로 push해.

기존 기록: [changho-2026-11-15](experiment-results/changho-2026-11-15/summary.md).
이 기록의 5% pilot과 새 공통 평가셋은 서로 다른 cohort다.
