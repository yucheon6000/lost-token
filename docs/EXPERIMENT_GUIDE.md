# Lost Tokens 공통 실험 가이드

이 문서는 여러 사람이 Claude/Codex로 같은 문제를 평가하고 결과를 공유하기 위한 실행 규약이다.
Claude는 이 문서와 루트 `CLAUDE.md`, `AGENTS.md`를 먼저 읽는다.
사용자의 명시적 지시가 우선하며, 단순 문서·상태 요청을 실험 실행으로 확대하지 않는다.

## 1. 진행 방법

1. `git status`와 현재 브랜치를 확인한다. 다른 사람의 변경을 지우거나 임의로 stash하지 않는다.
2. 실행 코드 checkout에서 개인 브랜치 `{name}-{date}`를 만든다. 처음에는
   `origin/changho-2026-11-15`의 검증된 실행 코드를 사용할 수 있다. 공용 허브는 실행 코드가 없다.
   이름은 사용자의 이름/별칭, 날짜는 `YYYY-MM-DD` 형식의 작업 시작일이다.
   날짜가 바뀌어도 재개 중인 브랜치/실험 이름은 바꾸지 않는다.
3. 변경 전 `temp/snapshots/`에 원본을 보존한다. 방법론은 한 요소씩 바꿔 비교한다.
4. `uv sync --frozen`으로 프로젝트 로컬 환경을 준비한다. 시스템 Python에 설치하지 않는다.
5. 데이터를 준비하고 고정 cohort를 검증한다. ID 검증 실패 시 중단하고 원인을 해결한다.
6. CPU 테스트를 실행하고, GPU 여유와 다른 사용자의 프로세스를 확인한다.
7. GPU/디코딩 변경이면 **최종 답이 실제로 추출되고 채점되는** 소규모 GPU 검증을 먼저 한다.
   토큰 cap으로 정답이 없는 smoke만 통과한 것으로 채점 경로까지 검증했다고 보고하지 않는다.
8. 같은 backend/config/ID/seed/output budget으로 baseline과 ours를 순서대로 실행한다.
   일반적으로 GPU당 독립 모델 1개, vLLM case batch 최대 8개를 사용한다.
   GPU 8개를 확보했다면 `--gpus 0,1,2,3,4,5,6,7`을 사용한다. 다른 작업의 GPU는 쓰거나 종료하지 않는다.
9. 모든 완료 실행의 audit를 확인하고 결과 문서 세 개를 작성한다.
10. 코드·설정·테스트는 개인 브랜치로 push한다. 결과 폴더는 공용 `shared-evaluation`으로
    별도 제출하고, 통합 비교표를 갱신해 다른 사람의 기존 결과와 함께 보여준다.

### 설치와 실행 예시

아래 `MYNAME`, `YYYY-MM-DD`, 방법 설명/가설을 실제 값으로 바꾼다.
`uv`가 없으면 저장소 quickstart의 로컬 uv 설치 절차를 사용하며 시스템 환경을 수정하지 않는다.
명령은 저장소 루트에서 실행한다.

```bash
git fetch origin
git switch -c MYNAME-YYYY-MM-DD origin/changho-2026-11-15
git worktree add --detach .shared-evaluation origin/shared-evaluation
uv sync --frozen
uv run --frozen python scripts/shared_eval.py prepare \
  --name MYNAME --date YYYY-MM-DD --work-dir workspace
uv run --frozen python scripts/shared_eval.py check \
  --name MYNAME --date YYYY-MM-DD --work-dir workspace
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python scripts/shared_eval.py run \
  --name MYNAME --date YYYY-MM-DD --work-dir workspace \
  --config configs/vllm-argmax.json --gpus 0,1,2,3,4,5,6,7 \
  --method-description 'rank-1 고정 선택과 대안 추론 메모리 삽입' \
  --hypothesis 'confidence 기반 lookahead 선택을 제거하면 수학 추론 오류가 줄어든다'
```

`prepare`는 pinned 데이터/모델을 내려받고 정규화한다. 기존 모델 캐시가 있으면
모든 명령에 `--model-cache /path/to/shared/model-cache`를 동일하게 전달한다.
공유 모델 캐시는 읽기 재사용하고, 실행 출력과 `.venv`는 작업자별로 분리한다.
`run`은 데이터셋별 baseline/ours를 실행하고 `workspace/shared-studies/{name}-{date}/submission/`에
결과 문서·환경·submission.json을 만든다. 이 폴더는 개인 브랜치에 commit하지 않는다.
다른 공용 checkout을 사용하면 `--shared-root /path/to/shared-checkout`을 전달한다.
일부 데이터셋만 실행하려면 `--benchmarks aime25 hmmt25`처럼 명시하고 부분 결과라고 보고한다.

기본 ours는 `configs/vllm-argmax.json`이다. lookahead 대조군은
`configs/vllm-lookahead.json`이며, **둘 다 메모리를 사용하는 ours 계열**이다.
새 방법은 별도 config와 코드 diff로 남기고 `--method-description`에 실제 동작을 설명한다.

## 2. 데이터셋과 공통 고정 서브셋

**정본은 `shared-evaluation` 브랜치의 `evaluation/subsets/shared-v1/*.json` 문제 ID 목록이다.**
비율만 같게 새로 추첨하는 것은 허용하지 않는다. 모두 동일 파일을 사용한다.

| CLI 이름 | 데이터셋/원본 split | 전체 n | 공통 평가 n | 평가 범위 | 고정 ID 파일 |
|---|---|---:|---:|---|---|
| `aime25` | MathArena AIME 2025 | 30 | 30 | 전체 | `aime25.json` |
| `hmmt25` | MathArena HMMT February 2025 | 30 | 30 | 전체 | `hmmt25.json` |
| `gsm8k` | OpenAI GSM8K `main/test` | 1,319 | 1,319 | 전체 | `gsm8k.json` |
| `gpqa` | GPQA **Main**, 공개 archive | 448 | 448 | **전체** | `gpqa.json` |
| `math500` | HuggingFaceH4 MATH-500 `test` | 500 | 250 | **50%** | `math500.json` |
| `mmlu` | cais/MMLU 57과목 `test` | 14,042 | 3,511 | **25%, 올림** | `mmlu.json` |

- GPQA Main과 Diamond는 다르다. 여기서는 Diamond로 대체하지 않는다.
- AIME/HMMT는 upstream parquet가 `train` 이름이더라도 이 저장소의 평가 문제 전체다.
- MMLU 학습/dev/few-shot 예제는 사용하지 않고 zero-shot 평가한다.
- 정답/참고 해설을 prompt에 넣지 않는다. 정답은 채점에만 사용한다.
- MATH500은 `(subject, level)`, MMLU는 `subject`로 층화했다.
- 층별 개수는 largest-remainder 방식으로 배분하고, 층 안에서는
  `SHA256("lost-tokens/shared-v1/{task}/{id}")` 순서로 고정했다.
  정답·모델 출력·이전 실험 성공 여부는 추출에 사용하지 않았다.
- MMLU `ceil(14042 × .25) = 3511`로 정했다. 정확한 과목별 수는 manifest에 기록돼 있다.
- manifest는 ID 파일 SHA256, 정규화된 선택 행 해시, dataset revision/source 정의,
  adapter hash, tokenizer/model revision, 데이터 설정을 포함한다.
- 일상 실험에서 `freeze_shared_subsets.py`를 다시 실행하지 않는다. 변경은 합의 후
  `shared-v2` 같은 **새 버전**으로 추가하고 기존 정본을 보존한다.
- `--limit`, 각자 만든 `random.sample`, 과거 5% pilot ID 파일로 대체하지 않는다.
- SuperGPQA/LongBench v2는 현재 공통 필수 평가 범위에 포함하지 않는다.

직접 CLI를 사용하는 경우에도 반드시 동일 ID 파일을 전달한다.

```bash
uv run --frozen lost-tokens run --config configs/vllm-argmax.json \
  --benchmarks math500 --arms baseline ours --gpus 0,1,2,3,4,5,6,7 \
  --ids-file .shared-evaluation/evaluation/subsets/shared-v1/math500.json \
  --run-name MYNAME-YYYY-MM-DD-shared-v1-math500
```

## 3. 비교 조건과 기록해야 할 방법론

기준 generator는 `Qwen/Qwen3-4B-Thinking-2507`, BF16, pinned revision이다.
기본 sampling은 temperature 0.6 / top-p 0.95 / top-k 20, experiment seed 95021,
데이터 shuffle seed 20260921, 입력/생성 body cap 각각 32,768토큰이다.
반복 억제는 양쪽 모두 ON이다. 표준 backend는 pinned vLLM 0.10.2 V0이다.

- **baseline**: 일반 autoregressive sampling (`plain_ar`), 분기/메모리 삽입 없음.
- **ours**: 제안 방법. 기본 설정은 rank-1 고정 선택, 64토큰 rollout, 대안 메모리 삽입,
  원확률 0.2 분기 조건, 최소 간격 256 body tokens, cosine 중복 기준 0.85이다.
- 제안 방법과 무관한 model/precision/backend/seed/prompt/scorer/output budget은 동일하게 유지한다.
- 모델이나 sampling 자체를 연구 변수로 바꾸면 별도 연구임을 명시하고 matched baseline도 실행한다.
- Transformers와 vLLM은 같은 seed여도 토큰이 동일하다고 가정하지 않는다.
  backend를 바꿨으면 baseline과 ours 모두 같은 backend에서 평가한다.
- 코드 변경점, 가설, config 전체, commit/source hash, cohort version/manifest hash,
  GPU 종류/수, 라이브러리 버전, 시간 측정 범위, audit 결과를 기록한다.
- 단일 seed와 부분셋의 작은 차이를 통계적으로 확정된 개선이라고 쓰지 않는다.

## 4. Resume와 실패 처리

`shared_eval.py run`에 **동일한 인자와 작업 시작일**을 다시 전달하면 기존 study와 run을 재개한다.
이미 완료된 arm/문제/모델 호출은 재사용하며 진행 중 저장되지 않은 호출만 다시 계산한다.
작업자는 같은 work-dir, 모델 cache, 코드, config, runtime을 유지해야 한다.

단일 run 재개는 다음과 같다.

```bash
uv run --frozen lost-tokens resume --run workspace/outputs/RUN_NAME
uv run --frozen python scripts/shared_eval.py report --name MYNAME --date YYYY-MM-DD
```

- 실행 중 code/config를 수정하거나 shared `.venv` 패키지를 바꾸지 않는다.
- identity 검사 실패를 지우거나 hash를 덮어써서 강제로 resume하지 않는다.
- 수정이 필요하면 기존 실행/소스를 보존하고 새 run을 만든다.
- scoring-only 체크포인트 이관은 `fork_inference_checkpoints.py`의 엄격한 검증 범위에서만
  허용된다. 생성 코드/설정/데이터/runtime 동일성과 원본 해시, 새 provenance를 보존한다.
- 실패하면 상태·원인·복구·재사용 범위를 보고하고, 새 ETA는 실제 정상 실행에 근거해 갱신한다.

## 5. 결과 Markdown과 push 규칙

### 환경 기록 (필수)

`shared_eval.py run`은 시작 전에 `environment.json`을 자동 생성한다.
로컬 study plan과 제출 폴더에 함께 보존하고, 각 완료 run은
`reports/<task>/worker-environments.json`에 worker별 identity 환경도 저장한다.

- 실제 사용 GPU 모델명, **장수**, CLI 번호, physical 번호/UUID, 장당 VRAM.
- NVIDIA 드라이버, CUDA runtime, Python/OS/CPU 아키텍처, CPU 수와 host RAM.
- PyTorch, Transformers, vLLM, tokenizer 등 주요 패키지의 정확한 버전.
- 모델/revision, BF16 등 정밀도, backend, GPU worker 수, TP 크기,
  GPU당 동시 case 수, batch token 상한, GPU memory fraction.
- 수집 시각과 CUDA_VISIBLE_DEVICES 등 허용 변수. 토큰/비밀번호를 포함한 전체 env는 저장하지 않는다.
- GPU 종류/수 변경, 공유 사용, 중단/재개의 시간 비교 영향.

재개 시 기존 환경 기록을 덮어쓰지 않는다. 추가 관측은 별도 시각/파일로 남긴다.
과거 실험의 사후 수집값은 실행 당시 실측처럼 쓰지 않고 사후 관측이라고 표시한다.

## 6. 브랜치 역할과 결과 제출

| 브랜치 | 저장 내용 | Push 대상 |
|---|---|---|
| `{name}-{YYYY-MM-DD}` | 구현 코드, configs, tests, lock/dependency, 실행 스크립트 | 자기 개인 브랜치 |
| `shared-evaluation` | 정본 guide/Claude 문서, 고정 ID/manifest, 모든 실험 결과와 비교표 | 공용 브랜치 |

main에 직접 push하거나 force-push하지 않는다. **개인 브랜치 전체를 공용 브랜치에 merge하지 않는다.**
개인 브랜치에 공용 guide/ID/실험 결과를 중복 commit하지 않는다. 개인 CLAUDE.md는 정본 링크만 둔다.
작업 시작일은 YYYY-MM-DD이며, 날짜가 바뀐 resume는 원래 개인 브랜치와 `--date`를 유지한다.

실험 전에 코드/설정을 개인 브랜치에 commit하여 정확한 code commit을 기록한다.
`shared_eval.py`는 code branch/commit, source fingerprint, 사용한 공용 commit과 cohort hash를 기록한다.
코드가 바뀐 상태에서 과거 study를 강제로 재개하지 않는다.

### 제출 구조

```text
# 개인 code checkout: 로컬 산출물, Git에 넣지 않음
workspace/shared-studies/{name}-{date}/submission/

# 공용 브랜치: 위 산출물만 복사해서 제출
experiment-results/{name}-{date}/
  baseline.md
  ours.md
  method.md
  environment.json
  submission.json
  study-plan.json
  reports/...
```

- baseline.md: 일반 AR correct/n, 정확도, 시간, 조건, audit/출처.
- ours.md: 제안 방법 correct/n, baseline 차이, 가능하면 paired wins/losses.
- method.md: 가설, 실제 구현, 개인 code branch와 **code commit**, config, source/cohort hash, 한계.
- environment.json: 앞 절의 실제 GPU 종류/장수/번호와 전체 runtime 설정.
- submission.json: 통합 비교표를 만드는 기계 판독 metadata. 수치는 artifact에서 계산한다.

일부/실패/미측정은 그대로 표시한다. 미측정 baseline을 lookahead나 다른 backend/과거 점수로 대체하지 않는다.
새 공통 평가와 과거 pilot은 cohort가 다르므로 분리한다. 비교표는 cohort/모델/revision/backend/seed/정밀도/채점 hash별로 그룹화한다.
원본 모델/데이터/환경/대규모 추론 checkpoint·비밀정보는 올리지 않는다.
과거 결과에 포함된 source-snapshot/provenance는 동결된 재현 증거이며 이 허브에서 수정/개발하지 않는다.

### 코드 push (개인 브랜치)

```bash
uv run --frozen ruff format --check src tests scripts
uv run --frozen ruff check src tests scripts
uv run --frozen python -m unittest discover -s tests -v
git diff --check
# 자기 구현 변경만 stage; workspace 결과, 공용 checkout은 제외한다.
git add src configs tests scripts pyproject.toml uv.lock
git commit -m 'Implement METHOD and record experiment settings'
git push -u origin MYNAME-YYYY-MM-DD
```

### 결과 push (공용 브랜치)

먼저 공용 worktree가 clean인지 확인한다. 다른 사람의 변경을 지우지 않는다.
공용 checkout을 최신 커밋으로 갱신한 **뒤** 자기 결과 폴더를 복사한다.

```bash
git -C .shared-evaluation status --short
git -C .shared-evaluation fetch origin shared-evaluation
git -C .shared-evaluation switch --detach origin/shared-evaluation
test ! -e .shared-evaluation/experiment-results/MYNAME-YYYY-MM-DD
cp -a workspace/shared-studies/MYNAME-YYYY-MM-DD/submission \
  .shared-evaluation/experiment-results/MYNAME-YYYY-MM-DD
uv run --frozen python .shared-evaluation/tools/results.py validate \
  --root .shared-evaluation --submission MYNAME-YYYY-MM-DD
uv run --frozen python .shared-evaluation/tools/results.py index --root .shared-evaluation
git -C .shared-evaluation add experiment-results/MYNAME-YYYY-MM-DD \
  experiment-results/README.md experiment-results/comparison.csv
git -C .shared-evaluation diff --cached --check
git -C .shared-evaluation commit -m 'Add MYNAME experiment results and refresh comparison'
git -C .shared-evaluation push origin HEAD:shared-evaluation
```

동시에 다른 사람이 제출해서 push가 거절되면 공용 worktree에서 `fetch` 후 자기 결과 commit을
최신 `origin/shared-evaluation` 위로 rebase한다. 비교표 충돌은 수치를 손으로 합치지 말고
`tools/results.py index`로 재생성해 해결한다. 기존 제출 폴더는 덮어쓰지 않는다.
같은 ID를 수정해야 하면 작성자와 버전 보존 방법을 확인하고 진행한다.

수치/표를 직접 조작하지 않는다. `experiment-results/README.md`와 `comparison.csv`는 생성물이다.
공용 브랜치의 CI도 제출 구조와 비교표 일치 여부를 검사한다.
Push 권한/branch protection 때문에 막히면 결과 commit을 보존하고 해당 사유를 보고한다.
사용자가 push를 명시했다면 반복 확인을 요청하지 않고 승인된 범위에서 진행한다.
