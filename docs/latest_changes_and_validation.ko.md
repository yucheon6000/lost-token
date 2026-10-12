# 최신 Lost Tokens 변경 사항과 검증 계획

현재 구현은 모델 가중치를 바꾸지 않는 training-free 추론 방식이다.
문장 종료 판정, 답변 예산, 분기 기준, 최근 대안 중복 검사를 수정했다.
CPU 테스트 176개는 통과했다. 최신 설정의 GPU 추론 검증과 12시간 성능 비교는
아직 실행하지 않았다. 준비했던 실험은 시작 전에 취소하고 이 브랜치로 정리했다.

## 바뀐 설정

설정 진입점은 [sparse-sentence-rollouts.json](../configs/sparse-sentence-rollouts.json)이다.

| 항목 | 이전 12시간 실험 설정 | 현재 설정 |
|---|---:|---:|
| 최소 분기 간격 | 본문 256토큰 | 본문 **1,024토큰** |
| 최소 raw entropy | 1.0 nats | **1.3 nats** |
| 강제 추론 종료 위치 | 31,743토큰 | **30,719토큰** |
| 답변 예약량 | 1,024토큰 | **2,048토큰** |
| 후보 수 | Original / Unchosen 두 개 | 동일 |
| 후보 종료 | 문장부호 기반 끝 두 번 | 수식·코드 문맥을 반영한 끝 두 번 |
| 현재 분기 내 cosine 기준 | 0.85 | 동일 |
| 최근 보관 대안과 추가 비교 | 없음 | 최근 **4개**, cosine **>= 0.85**이면 제외 |

분기 횟수 상한은 추가하지 않았다. `branch_tokens: 32`는 기존 토큰 길이
모드에만 적용하며, 현재 두 문장 모드에는 고정 32·64토큰 상한이 없다.
EOS, 추론 종료 마커, 남은 본문 예산, 실행 마감 시간은 계속 적용한다.

## 구현에서 달라진 동작

### 문장 종료

`26!`, `n!`, `(n-1)!`의 팩토리얼을 문장 끝으로 세지 않는다.
소수점, 약어, initialism, 번호 목록, 이스케이프된 문장부호도 구분한다.
`$...$`, `$$...$$`, `\(...\)`, `\[...\]`, 인라인 코드와 fenced code 내부의
문장부호는 제외한다. 긴 수식이 여러 토큰에 걸쳐 이어지거나 분기가 수식
중간에서 시작해도 문맥을 유지한다. 전각 문장부호는 공백 없이 인식한다.

여전히 문장부호와 문맥에 기반한 규칙이다. 모든 언어와 수학 표기의 문법을
완전히 분석한다고 주장하지 않는다. 수식·코드가 닫히지 않거나 실제 문장
끝이 나오지 않으면 다른 예산 제한이 먼저 후보를 끝낼 수 있다.

### 강제 종료와 reasoning 재진입

열린 추론은 본문 30,719토큰에서 `</think>` 한 토큰으로 닫는다.

```text
추론 30,719 + 종료 경계 1 + 답변 최대 2,048 = 본문 최대 32,768
```

강제 종료 설정이 있으면 자연 종료·강제 종료 뒤 답변 단계에서 `<think>`와
`<reasoning>` 재출력을 마스킹한다. 여러 텍스트 토큰으로 나뉜 마커도 검사하고,
차단 후 top-k를 다시 채운 다음 top-p 샘플링한다. EOS는 차단하지 않는다.
이 상태는 체크포인트 재개 시에도 복원하며, 답변 단계에서는 분기하지 않는다.
초기 지시문에도 추론 종료 뒤 최종 답변만 작성하도록 짧은 지시를 추가했다.

일반 문장으로 재검토하는 행동까지 완전히 강제하지는 못한다. 2,048토큰
예약이 정답이나 답변 완성을 보장하지도 않는다. 32k는 생성 본문 한도이며,
후보 생성·삽입 메모리·전체 forward 계산량까지 합친 예산은 아니다.

### 최근 대안과의 중복 검사

먼저 기존 방식대로 현재 분기의 Original과 Unchosen을 비교한다.
이를 통과한 Unchosen만 현재 메모리에 남아 있는 최근 대안 4개와 추가로
비교한다. 어느 하나와 cosine이 0.85 이상이면 새 대안을 메모리에 넣지 않는다.

- 이미 보관한 대안의 임베딩을 재사용한다. 과거 대안을 다시 임베딩하지 않는다.
- 최근 창에는 실제 보관한 대안만 들어간다. 탈락한 후보는 창을 갱신하지 않는다.
- 압축·만료로 제거된 메모리는 비교에서 제외한다.
- 대안이 중복으로 탈락해도 Original은 생성한 그대로 본문에 커밋한다.
- 비교 대상 이벤트·rank·벡터·판정을 체크포인트에 기록하고 감사에서 재구성한다.

이 검사는 후보 생성 **후**에 적용한다. 중복 메모리 삽입은 줄이지만 이미
지출한 후보 생성 비용을 없애지는 않는다. 의미가 다르다는 사실과 수학적으로
옳다는 사실도 구분해야 한다. 최근 창 크기는 `similarity.recent_alternatives_window`
에서 조절하며, 생략하거나 0으로 설정하면 기존 분기 내 비교만 사용한다.

## 기존 결과에서 확인한 문제

아래 결과는 **이전 설정**의 결과다. 현재 설정의 성능으로 해석하면 안 된다.
AIME25/HMMT25를 세 방법에 각각 4시간씩 실행했으며, 공통 완료 11문제 기준이다.

| 방법 | 정답 | 평균 문제당 시간 |
|---|---:|---:|
| 순정 plain AR | 7/11 | 14.81분 |
| 기존 Lost Tokens | 8/11 | 16.22분 |
| 이전 최신 설정 | 9/11 | 20.67분 |

이전 최신 설정은 순정보다 39.52% 느렸다. 단일 시드와 작은 완료 표본이며,
순정 대비 정확 McNemar p=0.5이므로 정확도 개선을 확정할 수 없다.
같은 공통 문제에서 기존 대비 분기 횟수는 747회에서 738회로 1.20%만 줄었다.
평균 후보 길이는 약 32토큰에서 74.46토큰으로 늘었다. 후보 생성과 Original
재처리가 이전 최신 설정 소요시간의 약 47.58%, 임베딩이 약 3.03%였다.

완료 문제에서 강제 종료가 발동한 사례는 없었다. 팩토리얼을 문장 끝으로
오인해 일부 후보가 일찍 끝난 사례는 확인했다. 각각의 기능이 정답 변화에
기여했는지는 이 전체 방법 비교만으로 분리할 수 없다.
기존 실행 식별자는 `bench12h-fixed-20261011T101050Z-f7842d`이며, 원본 trace와
보고서는 로컬 `outputs/`에 보존했다. 원본 실행 산출물은 이 브랜치에 포함하지 않는다.

## 완료한 검증

- [x] CPU 테스트 176개 통과. [문장 판정](../tests/test_sentence_boundaries.py),
  [최근 대안 검사](../tests/test_recent_alternatives.py),
  [강제 종료·답변 모드](../tests/test_three_features.py) 회귀 테스트 포함.
- [x] 실제 Qwen 토크나이저로 720토큰의 긴 수식·한국어 혼합 입력을 검사.
  문장 끝 세 개를 올바르게 세고 스트리밍 복원 텍스트가 일치하는 것을 확인.
- [x] 실제 토크나이저의 native `<think>`와 텍스트로 나뉜 `<reasoning>` 재진입
  차단, EOS 허용을 확인. 이 검사는 토크나이저와 합성 logits를 사용한 CPU 검사다.
- [x] 중복·새 대안·빈 창·비활성 창·cosine 경계값을 검사.
- [x] 메모리 만료·압축 후 비교 창, Original의 정확한 커밋, 중단 후 재개,
  기존 체크포인트 보존, 비교 기록 변조에 대한 감사 실패를 검사.
- [x] 새 설정과 순정 설정에서 AIME25/HMMT25 각 30문제의 질문·순서 일치를 확인.

## 다음 검증 항목

1. **실제 GPU smoke와 재개.** 고정 Qwen3-4B-Thinking-2507 BF16으로 자연 종료,
   강제 종료, 답변 단계 마스킹, 두 후보의 독립 KV, 메모리 삽입·중복 탈락,
   압축·만료, 선택 커밋, 중단 후 재개와 감사를 확인한다. CPU·토크나이저
   검사를 GPU 추론 검증으로 대신하지 않는다.
2. **문장 판정의 실제 trace.** 팩토리얼, 긴 수식, 코드, 약어, 여러 언어와
   미완성 delimiter 사례를 검토한다. 잘못 세어 일찍 끝나는 경우와 문장이
   끝났는데 계속 생성하는 경우를 모두 기록한다. 임베딩 4,096토큰·이벤트
   메모리 8,192토큰 한도 초과도 오류를 명확하게 기록하며 조용히 자르지 않는다.
3. **2k 답변 예약의 효과.** 강제 종료 발동 수, 닫힌 위치, 남은 답변 토큰,
   최종 답변 추출·완성·정확도, reasoning 재진입과 일반 문장 재추론을 각각
   측정한다. 강제 종료가 발동하지 않았다면 효과 미검증으로 남긴다.
4. **12시간 비교.** AIME25/HMMT25, 순정·기존·현재 설정을 각각 최대 4시간
   실행한다. 모델 revision·dtype·장치·시드·질문 순서·샘플링을 맞춘다.
   초기 지시문과 강제 종료 등이 다른 전체 방법 비교임을 명시한다.
5. **시간과 정보 가치.** 공통 문제의 정답률·승패·시간, 완료 문제 수,
   body tokens/s, forward 토큰, 분기 간격·횟수, 후보 길이, 메모리 삽입률,
   최근 중복 탈락률, 후보·재커밋·임베딩 비용, peak GPU/CPU 메모리를 기록한다.
   최근 대안 비교로 생성 비용 자체가 줄었다고 주장하지 않는다.
6. **통계와 분리 실험.** 여러 시드와 더 큰 공통 문제 집합에서 확인한다.
   1,024 간격·1.3 entropy·최근 대안 검사·2k 예약을 각각 분리해 비용과
   정확도 영향을 확인한다. threshold만 바꾼 과거 분기 후처리 수치를 실제
   새 생성의 분기 감소율로 해석하지 않는다.
7. **릴리스 검증.** Ruff lint는 통과했지만 현재 `ruff format --check src tests`
   는 9개 파일에서 미통과다. 기존 파일과 이번 수정 파일이 함께 포함돼 있다.
   포맷 게이트와 GitHub Actions 결과를 확인하고, wheel 설치·다른 작업 디렉터리·
   GPU/worker 수 변경 검증을 현재 소스로 다시 수행한다. 이전 버전의 릴리스
   검증을 현재 버전의 검증으로 간주하지 않는다.

## 재현과 실행 시 주의점

환경 구성은 프로젝트 로컬 `uv` 환경과 잠긴 의존성을 사용한다.

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check src tests
uv run --frozen ruff format --check src tests
```

최신 프로파일에서 `plain_ar`만 선택해도 초기 지시와 강제 종료 설정은 적용된다.
따라서 순정 baseline은 패키지 기본 설정으로 따로 실행해야 한다.
아래 명령은 GPU smoke 이후 실행할 비교 예시이며, 이 문서 작성 시 실행하지 않았다.
모델과 pinned 원본 데이터가 이미 준비된 환경을 가정한다. 새 환경의 준비 과정은
[README](../README.md)를 따른다. GPU 0은 예시다. 할당된 장치를 확인하고
실행마다 새로운 식별자를 사용한다.

```bash
RUN_ID=sparse-v2-$(date -u +%Y%m%dT%H%M%SZ)
uv run --frozen lost-tokens prepare --work-dir workspace --benchmarks aime25 hmmt25
uv run --frozen lost-tokens prepare --work-dir workspace --benchmarks aime25 hmmt25 \
  --config configs/sparse-sentence-rollouts.json

uv run --frozen lost-tokens run --work-dir workspace --benchmarks aime25 hmmt25 \
  --gpus 0 --arms ours --hours-per-arm 4 --run-name "$RUN_ID-current" \
  --config configs/sparse-sentence-rollouts.json
uv run --frozen lost-tokens run --work-dir workspace --benchmarks aime25 hmmt25 \
  --gpus 0 --arms baseline --hours-per-arm 4 --run-name "$RUN_ID-baseline"
uv run --frozen lost-tokens run --work-dir workspace --benchmarks aime25 hmmt25 \
  --gpus 0 --arms ours --hours-per-arm 4 --run-name "$RUN_ID-legacy"

uv run --frozen python scripts/compare_runs.py \
  "workspace/outputs/$RUN_ID-baseline" "workspace/outputs/$RUN_ID-current" \
  "workspace/outputs/$RUN_ID-legacy" \
  --baseline "workspace/outputs/$RUN_ID-baseline:baseline"
```

중단된 실행은 기존 `run`에 맞는 소스·설정으로 재개하고 저장된 마감 시간을 유지한다.
타이머를 다시 설정하거나 다른 실행을 덮어쓰지 않는다. 진행률·ETA·로그·체크포인트·
해석된 설정·소스와 입력의 식별 정보를 같은 run ID 아래에 보존한다.
