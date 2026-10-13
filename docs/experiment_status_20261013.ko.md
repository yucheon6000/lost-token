# Sparse reasoning v2 실험 결과와 진행 상황

기준일: 2026-10-13, 시간대: KST. 브랜치: `feature/sparse-reasoning-v2`.

AIME25/HMMT25 비교는 완료했다. 같은 Qwen3-4B 모델에서 baseline은 34/60,
Ours는 39/60을 맞혔다. 정답률은 **+8.33%p**, 평균 문제 처리 시간은
**+12.38%** 증가했다. 단일 시드의 전체 방법 비교 결과다.

남은 실행 대상은 **GPQA, MMLU, LongBench v2**다. SuperGPQA는 실행 시간이
길다는 판단에 따라 이번 계획에서 제외했다. MMLU 지원과 속도 보고 코드를
추가했으며, 아래의 짧은 검증과 본 벤치마크 성적은 구분한다.

## 1. 진행 상황

| 작업 | 상태 | 확인 내용 |
|---|---|---|
| 레포 이해·검토 | 완료 | 분기 후보, 선택 커밋, 메모리, 재개·감사 흐름 검토 |
| 초기 문제 수정 | 완료 | README clone 대상 수정, 포맷 게이트 정리 |
| 실행 환경 | 완료 | 프로젝트 로컬 uv 환경, 잠긴 의존성 사용 |
| 기존 데이터·모델 확인 | 완료 | 기존 5개 벤치마크 원본 10파일 해시 검증, 누락 없음 |
| 결과 보존 최적화 | 완료 | CPU 반복 작업 축소, Qwen3 MLP/RMSNorm CUDA graph 재사용 |
| GPU 수치·재개 검증 | 완료 | 4개 GPU에서 수치 일치, smoke 8개 워커 검증 통과 |
| AIME25/HMMT25 본 실험 | 완료 | 두 방법 각각 60/60, 최종 8개 워커 검증 통과 |
| MMLU 데이터 지원 | 완료 | 고정 revision·SHA256, test 14,042문제·57과목 |
| MMLU 전처리 | 완료 | baseline/Ours 질문·순서·정답 일치 확인 |
| 속도 손해 보고 | 완료 | JSON·Markdown·워커 로그·상태 로그에 시간과 계산량 기록 |
| GPQA/MMLU/LongBench v2 본 실험 | 미실행 | 실행 범위와 시간 예산 결정 필요 |

멀티시드는 수행하지 않았다. 각 방법을 한 번 실행하고 초기 정상 동작을
확인한 뒤 정기 상태 점검 간격을 2시간으로 유지했다. 종료 이벤트는 별도로
확인했다. 16시간은 두 방법 합산 상한이었고, 전체 문제를 완료한 뒤 종료했다.

## 2. 모델과 비교 조건

| 항목 | 값 |
|---|---|
| Generator, 두 방법 공통 | `Qwen/Qwen3-4B-Thinking-2507` |
| Generator revision | `768f209d9ea81521153ed38c47d515654e938aea` |
| 정밀도 | BF16 |
| GPU | RTX 4090 24GB 4개, 두 방법이 같은 할당을 순차 사용 |
| 샘플링 | temperature 0.6, top-k 20, top-p 0.95 |
| experiment seed | 95021; 각 문제·위치의 시드는 결정적으로 파생 |
| 데이터 shuffle seed | 20260921 |
| 생성 본문 상한 | 문제당 32,768토큰 |
| 프롬프트 상한 | 32,768토큰 |
| Embedding, Ours | `Qwen/Qwen3-Embedding-0.6B`, CPU float32 |
| Embedding revision | `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` |
| 주요 런타임 | Python 3.12.4, PyTorch 2.6.0/CUDA 12.4, Transformers 4.57.1 |

Baseline은 일반 `plain_ar` 추론이다. 분기 정의 프롬프트, 분기 메모리,
답변 강제 종료와 반복 억제를 사용하지 않았다. 재현용 순정 설정은
[plain-ar-baseline.json](../configs/plain-ar-baseline.json)이다.

Ours는 [sparse-sentence-rollouts.json](../configs/sparse-sentence-rollouts.json)의
전체 방법이다. 최소 분기 간격 1,024 본문 토큰, 최소 raw entropy 1.3 nats,
후보 확률 0.2 이상, Original/Unchosen 최대 두 후보, 문장 끝 두 번을 사용한다.
최근 보관 대안 4개와 cosine 0.85 이상인 새 대안은 제외한다. 추론 30,719토큰
뒤 종료 경계 1토큰을 넣고 최종 답변에 최대 2,048토큰을 예약한다.

모델·가중치·정밀도·시드·질문·샘플링·본문 상한·GPU 할당은 같았다.
초기 프롬프트, 강제 종료, 반복 방지와 메모리는 다르다. 따라서 메모리 기능
하나만의 효과를 분리한 실험으로 해석하지 않는다. 본문 상한이 같더라도
후보 생성과 삽입 메모리를 포함한 총 계산량은 같지 않다.

## 3. 정확도 결과

| 벤치마크 | 공통 문제 | Baseline | Ours | 정답률 변화 | Ours 승/패 |
|---|---:|---:|---:|---:|---:|
| AIME25 | 30 | 21/30, 70.00% | 24/30, 80.00% | +10.00%p | 3/0 |
| HMMT25 | 30 | 13/30, 43.33% | 15/30, 50.00% | +6.67%p | 3/1 |
| 전체 | 60 | 34/60, 56.67% | 39/60, 65.00% | **+8.33%p** | **6/1** |

승은 baseline이 틀리고 Ours가 맞힌 문제, 패는 그 반대다. 두 방법 모두
전체 60문제를 완료해 이번 최종 표에는 시간 제한 때문에 빠진 문제가 없다.
단일 시드·60문제의 관측 결과이며 일반적인 개선이나 통계적 유의성을 확정하지 않는다.

## 4. 속도 손해와 계산량

시간 비교는 두 방법이 공통으로 완료한 **같은 문제**를 대상으로 한다.
평균 문제 처리 시간은 생성, 후보·메모리·임베딩 작업, 문제 단위 부가 작업을
포함하고 모델 로딩과 마지막 감사는 제외한다.

| 벤치마크 | Baseline 평균 초/문제 | Ours 평균 초/문제 | 시간 증가 | Forward 토큰 증가 |
|---|---:|---:|---:|---:|
| AIME25 | 442.39 | 511.86 | +15.70% | +17.98% |
| HMMT25 | 533.86 | 585.23 | +9.62% | +12.31% |
| 전체 | 488.13 | 548.54 | **+12.38%** | **+14.92%** |

```text
시간 증가율 = (Ours 공통 문제 처리 시간 합 / Baseline 같은 문제 처리 시간 합 - 1) × 100
```

양수는 더 느리다는 뜻이고 음수는 더 빠르다는 뜻이다. 서로 다른 완료 문제
집합이나 문제 수를 섞어 속도 증가율을 계산하지 않는다.

| 전체 60문제 지표 | Baseline | Ours |
|---|---:|---:|
| 문제 처리 시간 합, 워커별 시간 합산 | 29,287.57초 | 32,912.57초 |
| 문제 처리 시간 중앙값 | 464.90초 | 576.87초 |
| 생성 본문 토큰 | 1,421,584 | 1,313,801 |
| 본문 토큰 / 문제 처리 초 | 48.54 | 39.92 |
| Generator forward 토큰 | 1,432,163 | 1,645,867 |
| 후보 토큰 | 0 | 234,135 |
| 분기 이벤트 | 0 | 1,170 |
| 메모리 삽입 | 0 | 775 |
| 최근 대안 중복으로 탈락한 대안 | 0 | 3 |
| 임베딩 처리 시간 합 | 0초 | 731.48초 |

본문 길이가 달라졌으므로 tokens/s 변화와 문제당 시간 변화는 서로의 단순한
역수가 아니다. Forward 토큰은 논리적인 generator 계산량이며 GPU FLOPs를
측정한 값이 아니다. 임베딩 비용은 별도로 기록한다. 최근 대안 검사는 후보
생성 후 적용하므로 중복 탈락 3회를 후보 생성 비용 절감으로 해석하지 않는다.

실제 경과 시간은 baseline **06:04:54–08:41:37, 약 2시간 37분**,
Ours **08:41:37–11:40:37, 약 2시간 59분**이었다. 로딩·최종 감사를 포함한
총 경과 시간은 **약 5시간 36분**이다. 여러 워커의 문제 시간을 합산한 값과
병렬 실행의 경과 시간을 구분한다. 추론 phase의 경과 시간도 코드에서 별도로
기록하며 로딩·일시 중단은 포함하고 마지막 감사는 제외한다.

## 5. 추가한 속도 로깅 코드

[performance.py](../src/lost_tokens/performance.py)가 공통 문제의 시간·처리량과
계산량을 비교한다. [runner.py](../src/lost_tokens/runner.py)는 기존 trace 비용을
작은 outcome에 복사해 보고할 때 전체 토큰 trace를 반복해서 읽지 않도록 했다.
[reporting.py](../src/lost_tokens/reporting.py)는 보고서와 상태 로그에 연결한다.

| 저장 위치 | 기록 내용 |
|---|---|
| `workers/<worker>/outcomes/<task>/<id>.json` | seconds, body/forward/candidate tokens, generator/embedding/recovery seconds, memory insertions, timing_complete |
| `report.json` | `performance_vs_baseline`, 평균·중앙값 시간, timed_n, slowdown_percent, throughput 변화, 비용별 paired n, `phase_wall_seconds` |
| `report.md` | 벤치마크별 정확도·시간 증가·tokens/s·forward 토큰 증가 표 |
| 워커 로그 | 문제 완료 시 시간·본문/forward 토큰·임베딩 시간·시간 측정 유효 여부 |
| `health.json`, monitoring 로그 | 진행 중 paired 성능 지표 |
| 별도 실행 비교 | `scripts/compare_runs.py --output-dir ...`의 `comparison.json`, `comparison.md` |

중간 체크포인트부터 재개한 문제는 이전 작업 시간이 최종 재개 구간의
`seconds`에 포함되지 않으므로 두 방법의 시간 비교에서 함께 제외한다.
`timed_n`과 제외 수를 기록한다. 완료한 문제를 그대로 복원하면 원래 측정을
사용한다. 오래된 outcome의 누락 비용은 원본 case에서 읽을 수 있지만,
재개 여부를 확인할 메타데이터가 없으면 `timing_complete: null`과 unknown 수로
남긴다. 없는 시간·비용을 0으로 채우거나 속도 이득으로 계산하지 않는다.

원본 실행 파일을 바꾸지 않고 별도의 보고서를 생성하는 명령은 다음과 같다.

```bash
uv run --frozen python scripts/compare_runs.py \
  workspace/outputs/sparse16h-baseline-s95021 \
  workspace/outputs/sparse16h-ours-s95021 \
  --baseline workspace/outputs/sparse16h-baseline-s95021:baseline \
  --output-dir outputs/sparse16h-performance-20261013
```

## 6. 완료한 검증과 남은 해석

초기 upstream CPU 테스트는 176개, 결과 보존 최적화 후에는 186개가 통과했다.
4개 RTX 4090에서 prefix 0/2,048/8,192/32,768 토큰의 실제 GPU 수치 검사를
수행했고, 검사한 body/candidate/final 토큰과 raw log probability가 원본과
정확히 같았다. 이는 검사 범위의 증거이며 모든 입력에 대한 수학적 증명은 아니다.
GPU smoke의 중단·재개와 저장 체크포인트 보존도 확인했다.

본 실험 최종 감사는 8개 워커 모두 통과했다. 질문·정답과 60문제 완료 수,
소스·split·체크포인트 해시, 후보의 독립 root, 선택 rollout의 정확한 커밋,
cosine 재계산, 메모리 압축, reasoning 종료 뒤 비개입과 비용 합계를 검사했다.
원본 case의 정답 수를 별도로 집계해 보고서와 일치하는 것도 확인했다.

MMLU·속도 로깅 추가 후 공유할 소스와 테스트만 따로 추출해 CPU 테스트
**198개**, Ruff lint/format 검사를 통과했다.
MMLU 테스트는 원래 선택지 순서, test-only 데이터, subject·ID, 명시적인 답변
추출, 잘못된 선택지·정답·파일 해시 거부, CLI와 불균등 워커 분할을 다룬다.
시간 비교 테스트는 불일치 완료 집합, 빠른/느린 결과, 빈·누락·잘못된 시간,
재개 문제 제외, 세 방법의 pairwise 비교, JSON·Markdown 출력을 확인한다.

MMLU 실제 GPU smoke도 완료했다. baseline/Ours 각각 1문제, 두 워커의
중단·재개·체크포인트 보존·최종 감사를 통과했다. Ours에서 실제 분기 1회와
후보 33토큰을 확인했다. 재개한 두 문제는 `timing_complete: false`로 기록됐고
속도 비교의 `timed_n`에서 제외됐다. 짧은 smoke 성적은 본 벤치마크에 합산하지 않는다.
Wheel 빌드와 다른 작업 디렉터리에서의 MMLU CLI 다운로드 검증도 통과했다.

기능별 ablation, 실제 문장 경계의 상세 오류율, 강제 종료의 독립 효과와
긴 문맥에서의 GPU 메모리·비용 검증은 남아 있다. 멀티시드는 현재 실행 계획에
포함하지 않는다. 기존 3방법·12시간 계획은 이번의 2방법·단일 시드 비교와 구분한다.

## 7. 남은 벤치마크

| CLI 이름 | 평가 대상 | 문제 수 | 데이터 상태 | 본 실험 상태 |
|---|---|---:|---|---|
| `aime25` | AIME 2025 | 30 | 준비 완료 | 완료 |
| `hmmt25` | HMMT February 2025 | 30 | 준비 완료 | 완료 |
| `gpqa` | GPQA Main | 448 | 원본·해시 확인 완료 | 미실행 |
| `mmlu` | 57과목의 전체 test split | 14,042 | 다운로드·두 설정 전처리 완료 | 미실행 |
| `longbench_v2` | LongBench v2 | 503 | 원본·해시 확인 완료 | 미실행 |
| `supergpqa` | SuperGPQA | 26,529 | 원본·해시 확인 완료 | **이번 계획에서 제외** |

GPQA 어댑터의 기본 대상은 Main 448문제다. 그 안의 Diamond 198문제는
메타데이터로 구분되지만 기본 실행을 Diamond 전용 결과로 표기하지 않는다.

MMLU는 [cais/mmlu](https://huggingface.co/datasets/cais/mmlu/tree/c30699e8356da336a370243923dbaf21066bb9fe)
revision `c30699e8356da336a370243923dbaf21066bb9fe`의 `all/test`를 사용한다.
과목별 메타데이터와 원래 네 선택지 순서를 보존하며 zero-shot 생성 답변을
채점한다. 기본 보고서는 전체 문제를 합친 micro accuracy이며 과목별 macro
accuracy를 자동 계산하지 않는다. dev/train/validation, 5-shot 예시와 log-likelihood 채점은 사용하지
않는다. 따라서 그런 방식으로 보고된 공개 점수와 평가 조건을 맞춘 결과는 아니다.
원본 선택지와 답변 인덱스는 프롬프트·gold로 분리하고 정답을 프롬프트에 넣지 않는다.

LongBench v2는 현재 32K 프롬프트 상한에 맞춰 긴 context의 앞·뒤를 보존해
줄이는 어댑터다. 공식 전체 문맥 결과로 표기하지 않는다. 두 설정의 초기
지시 길이가 달라 유지한 context가 달라질 수 있으므로 본 실험 전에 유지
context·질문·선택지 일치와 긴 문맥 메모리 사용을 확인해야 한다.

## 8. 다음 실행 순서

1. GPQA, MMLU, LongBench v2 각각 baseline과 sparse 설정으로 전처리하고
   같은 평가 질문·gold·선택 순서를 고정한다. MMLU 전처리는 완료했다.
2. GPQA부터 작은 공통 집합으로 시간과 자원 사용을 측정하고 본 실행 예산을
   정한다. 이어서 MMLU, LongBench v2 순으로 진행한다. 아직 본 실행을 시작하지 않았다.
3. MMLU 전체는 14,042문제라 실행 범위와 시간 예산은 별도로 정한다.
   `--limit`는 seeded 전체 subset이며 과목별 층화 표본이 아니다. 과목별
   coverage가 필요하면 같은 고정 `--ids-file`을 두 방법에 사용한다.
4. 단일 시드·각 방법 한 번, 초기 확인 한 번, 이후 2시간 간격 점검을 유지한다.
   재개는 원래 소스·설정·마감 시간으로만 수행한다.
5. 각 결과에 정답률, 승패, `timed_n`, 시간 증가율, 평균·중앙값 시간,
   tokens/s, forward/candidate 토큰, 임베딩 시간과 실제 경과 시간을 함께 기록한다.
   예산 때문에 끝나지 않은 전체 벤치마크는 완료 subset의 크기와 선택 편향을 명시한다.

새 MMLU 실행 명령은 [README의 데이터·설정 절](../README.md#data-and-configuration)을
따른다. SuperGPQA를 제외한 계획에서는 `--benchmarks all` 대신 명시적인
벤치마크 목록을 사용한다.

## 9. 재현과 원본 산출물

본 비교의 소스 기준은 upstream 커밋
`1951748f3caf4ec25cd8ef62a63d77f7fc4c080e`에 로컬 결과 보존 최적화를 더한 상태다.
실험 시점의 전체 소스 해시, patch와 설정을 provenance에 저장했다.
이번 브랜치에 결과 보존 최적화, MMLU 지원과 속도 로깅을 함께 반영한다.
본 비교에서는 `model.exact_cpu_optimizations`와 `model.exact_stateless_graphs`를
두 방법 모두 켰다. 두 설정에 같은 스위치를 적용해야 한다. 기본값은 꺼져 있어
기존 경로로 실행할 수 있다. CUDA graph는 검증한 Qwen3·Transformers 버전의
단일 토큰 MLP/RMSNorm만 대상으로 하고 attention/KV/샘플링은 원래 경로를 쓴다.
새 어댑터·로깅 추가 뒤에는 소스 해시가 달라지므로 본 실험 당시 소스와 구분한다.
과거 실행을 재개하려면 당시 provenance의 소스를 사용해야 한다.
후속 실행은 실제 사용하는 소스·설정·런타임을 새 run에 고정한다.

원본 데이터는 기존 NAS의 `lost-tokens-benchmarks/inputs`를 재사용한다.
MMLU 두 원본 파일만 추가 다운로드했고 고정 해시를 검증했다. 데이터·모델·
생성 trace·체크포인트는 Git에 추가하지 않는다. 아래 경로는 실행 머신의
레포 루트 기준 로컬 산출물이며 새 clone에는 포함되지 않는다.

| 산출물 | 로컬 경로 |
|---|---|
| 원본 정확도 보고서 | `workspace/outputs/sparse16h/report.json`, `report.md` |
| 원본 상세 시간·비용 | `workspace/outputs/sparse16h/analysis.json` |
| 최종 검증 | `workspace/outputs/sparse16h/final-verification.json`, `final-case-hashes.json` |
| Baseline run | `workspace/outputs/sparse16h-baseline-s95021` |
| Ours run | `workspace/outputs/sparse16h-ours-s95021` |
| 당시 소스·설정·patch | `workspace/outputs/sparse16h/provenance`, `baseline.json`, `ours.json` |
| 추가 속도 보고서 | `outputs/sparse16h-performance-20261013/comparison.json`, `comparison.md` |
| MMLU 전처리 검증 | `outputs/mmlu-preparation.json` |
| MMLU GPU smoke | `workspace/outputs/mmlu-support-smoke-20261013` |
| 공유할 소스의 CPU 테스트 로그 | `logs/tests-staged-release-20261013-final.log` |

원본 보고서 식별용 SHA256:

```text
report.json             780987083e17f745fbb860c4bb5904a201899c3b5c5fc52ae2fb50de30d731a0
analysis.json           c0e0274b3a05da3b53802a261942abee3df65a8ca2ccb690b9256877a53432ee
final-verification.json 7f3de3caa265fd3cb4146fbce5981920bf10dd0929c2644211f232fddc3c5891
```

이전 구현 설명과 실행 전 계획은
[최신 변경 사항과 검증 계획](latest_changes_and_validation.ko.md)에 보존했다.
