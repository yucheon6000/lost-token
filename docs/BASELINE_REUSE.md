# 작업자별 baseline 1회 동결, 이후 ours-only 평가

**각 작업자는 자기 환경에서 일반 AR baseline을 한 번 완료해 고정한다.
그 뒤에는 모델 방법을 바꿀 때마다 ours만 실행하고, 처음 고정한 baseline으로 평가한다.**
다음 작업자도 자기 baseline을 먼저 측정한다. 다른 사람의 baseline이나 과거 pilot 점수로 대체하지 않는다.
GPU 프로필이 다르면 같은 사람도 프로필마다 별도 baseline을 만든다.

## 1. 첫 baseline을 전체 고정 ID에서 완료한다

[하드웨어 프로필](EVALUATION_PROFILES.md)을 선택하고 모든 작업자가 그 프로필의 같은 ID를 사용한다.
아래는 L40S 4 GPU 예시다. 코드 checkout에서 실행하며 `MYNAME`과 날짜를 바꾼다.
프로필 대응 코드는 `origin/ch-2026-11-15`를 기반으로 한다.

```bash
git fetch origin
git switch -c MYNAME-base-l40s-YYYY-MM-DD origin/ch-2026-11-15
git worktree add --detach .shared-evaluation origin/shared-evaluation
# 이미 공용 worktree가 있으면 위 add는 생략하고 현재 브랜치/내용을 먼저 확인한다.
# .venv는 개인 환경으로 준비한다.
uv sync --frozen
uv run --frozen python scripts/shared_eval.py prepare --profile l40s-4gpu \
  --name MYNAME-base-l40s --date YYYY-MM-DD --work-dir workspace
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python scripts/shared_eval.py run --profile l40s-4gpu \
  --name MYNAME-base-l40s --date YYYY-MM-DD --work-dir workspace \
  --gpus 0,1,2,3 --arms baseline \
  --method-description '일반 AR baseline 1회 측정 및 동결' \
  --hypothesis '이 작업자의 후속 ours 변형은 같은 baseline으로 비교한다'
```

코드/설정은 실행 전에 개인 브랜치에 commit한다. 공유 모델 캐시는 모든 명령에서 동일하게 지정한다.
PRO 6000은 별도 개인 브랜치에서 `--profile pro6000-8gpu --gpus 0,1,2,3,4,5,6,7`을 사용한다.

모든 요청 task의 **전체 고정 ID가 완료되고 audit를 통과해야** 다음 파일이 생성된다.

```text
workspace/shared-studies/MYNAME-base-l40s-YYYY-MM-DD/submission/baseline-reference.json
```

이 파일은 문제별 ID/정오답/예측, 원본 baseline run/코드 commit/소스 hash/환경/실측 시간과
비교 조건을 담는 해시 봉인된 reference다. 미완료/일부 baseline을 정식 reference로 동결하지 않는다.
`baseline.md`, `environment.json`, 원본 outputs/provenance도 함께 보존한다.
일부 task만 먼저 준비했다면 그 task에서만 재사용할 수 있고, 나머지 baseline은 먼저 완료해야 한다.

## 2. 새 방법부터는 ours만 실행한다

baseline을 동결한 코드 브랜치는 보존한다. 새 방법은 새 개인 브랜치/작업 ID로 만들고,
구현·설정·가설을 기록해 테스트/commit한 뒤 다음처럼 실행한다.

```bash
git switch -c MYNAME-ours-a-l40s-YYYY-MM-DD MYNAME-base-l40s-YYYY-MM-DD
# 여기서 ours 방법을 구현하고 config, 테스트, commit을 남긴다.
uv run --frozen python scripts/shared_eval.py run --profile l40s-4gpu \
  --name MYNAME-ours-a-l40s --date YYYY-MM-DD --work-dir workspace \
  --gpus 0,1,2,3 --arms ours \
  --baseline-ref workspace/shared-studies/MYNAME-base-l40s-YYYY-MM-DD/submission/baseline-reference.json \
  --config configs/vllm-argmax.json \
  --method-description '이번 ours 변형의 실제 동작과 변경점' \
  --hypothesis '고정 baseline에 비해 개선될 것으로 예상하는 이유'
```

방법 B/C도 각자 새 브랜치/작업 ID를 만들고 **같은 baseline-reference.json**을 전달한다.
`--arms ours --baseline-ref ...`는 baseline GPU worker를 만들지 않는다.
반대로 baseline-only 또는 baseline+ours 실행에 `--baseline-ref`를 붙이면 오류로 중단한다.
기존 방식의 첫 `--arms baseline ours` 실행도 지원하지만, 반복 실험의 기본 절차는 위 두 단계다.

진행 중 ours의 중단/재개는 원래 branch/date/config/reference를 유지한다.
새 방법으로 바꿀 때 기존 run을 강제 resume하지 않고 새 run을 만든다.
baseline의 추론 checkpoint를 ours run에 이식하거나 identity/hash를 덮어쓰지 않는다.
재사용하는 것은 **봉인된 AR 성능 결과와 provenance**다.

## 3. 비교할 때 고정할 조건

다음은 한 비교군 안에서 유지한다.

- 하드웨어 프로필, cohort 버전/manifest hash, 정확한 문제 ID, GPU당 batch.
- 모델/tokenizer revision, BF16 등 precision, backend/runtime/package 버전.
- prompt/data adapter, seed, temperature/top-p/top-k, 반복 억제, 출력 budget, 채점 조건.
- baseline 일반 AR의 동작. ours의 분기·선택·메모리 방법만 연구 변수로 바꾼다.

wrapper는 reference 내용 hash, cohort, 주요 모델/샘플링/채점/runtime 조건을 검사한다.
ours 구현 파일의 commit이 바뀌었다는 이유만으로 baseline을 다시 돌리지 않는다.
공유 생성 코드를 바꿨다면 AR 동작도 바뀌지 않았는지 diff를 검토하고 기록한다.
모델/seed/backend/문제/채점 등 비교 조건 자체를 바꾸거나 AR 동작을 바꾼 경우에만
**새 비교군과 새 baseline**을 만든다. 이전 baseline과 결과는 그대로 보존한다.

## 4. 성능 평가와 제출

각 ours의 제출 폴더에는 다음이 들어간다.

- `baseline.md`: 최초 고정 AR 점수, reference hash와 원래 실측 시간. 새로 실행한 시간처럼 쓰지 않는다.
- `ours.md`: 이번 ours 점수와 완료 범위.
- `baseline-reference.json`: 처음 동결한 reference의 동일한 사본.
- `reports/<task>/comparison.json`: 동일 ID 기준 paired 정확도 차이와 wins/losses.
- `method.md`: baseline 원본 branch/commit/reference hash, 이번 ours branch/commit/변경/가설.
- `environment.json`, `study-plan.json`, `submission.json`: 이번 환경, task별 config, 고정 reference identity.

미완료 ours는 공통 완료 ID만으로 paired 비교하고 부분 결과라고 명시한다.
baseline은 전체 고정 점수를 보존하며, 다른 문제 집합의 두 정확도를 단순히 빼서 개선이라고 쓰지 않는다.
새 방법 A/B/C는 같은 기준선에 대해 비교하고, 가장 유리한 baseline을 고르거나 덮어쓰지 않는다.

개인 코드 브랜치에는 구현만 push하고, 제출 폴더는 공용
`experiment-results/MYNAME-ours-a-l40s-YYYY-MM-DD/`에 추가한다.
`tools/results.py validate`는 reference hash와 제출 baseline 수치가 같은지도 검사한다.
각 작업자가 실험을 끝낼 때 **동결된 baseline reference와 사용 조건, ours별 비교 결과**를 남겨
다음 방법이 baseline 재측정 없이 이어질 수 있게 한다.

다음 사람은 이 문서와 정본 ID를 사용해 **본인 baseline부터 한 번** 측정한다.
시간 목표/문제 수는 프로필에 고정되어 있으며 ours를 바꿀 때마다 subset을 늘리거나 다시 뽑지 않는다.
