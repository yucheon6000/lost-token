# 하드웨어별 필수 고정 평가셋

**같은 프로필의 모든 작업자는 아래 정본 문제 ID를 그대로 사용한다.**
문제 수·비율만 맞춰 다시 추첨하거나 개인별 subset을 만들지 않는다.
실행 프로필의 정본은 [evaluation/profiles.json](../evaluation/profiles.json)이다.

| 항목 | L40S 4 GPU | 기존 PRO 6000 8 GPU |
|---|---|---|
| CLI | `--profile l40s-4gpu` | `--profile pro6000-8gpu` |
| GPU | NVIDIA L40S 4장, 장당 46,068 MiB 관측 | RTX PRO 6000 Blackwell 8장 |
| Cohort | **`l40s-2h-v1`** | **기존 `shared-v1`** |
| 정본 ID/manifest | [l40s-2h-v1](../evaluation/subsets/l40s-2h-v1/) | [shared-v1](../evaluation/subsets/shared-v1/) |
| AIME25 | **30** | **30** |
| HMMT25 | **25** | **30** |
| GSM8K | **1,319** | **1,319** |
| GPQA Main | **90** | **448** |
| MATH500 | **125** | **250** |
| MMLU | **550** | **3,511** |
| GPU당 batch | AIME/HMMT **4**, 나머지 **8** | 전 데이터셋 **8** |
| TP | 1, GPU마다 독립 모델 | 1, GPU마다 독립 모델 |
| 시간 목표 | 데이터셋별 **baseline+ours 합계 약 2시간** | 기존 고정 범위 유지, 2시간 제한 주장 없음 |

GPU 수는 데이터셋 하나에 배정하는 전체 장수다. 작업자 수나 GPU-hours를 뜻하지 않는다.
기준 모델은 Qwen3-4B-Thinking-2507/BF16, backend는 vLLM 0.10.2 V0이다.
기타 seed·sampling·prompt·채점·32K 출력 상한은 [공통 가이드](EXPERIMENT_GUIDE.md)를 따른다.

## 공통 ID 사용과 결과 구분

- PRO 6000의 `shared-v1` ID 파일과 manifest는 **바이트 단위로 그대로 보존**했다.
- L40S의 여섯 ID 파일은 승인된 측정 권장안과 **동일한 파일**이다. 재생성하지 않는다.
  기존 `shared-v1` 내부에서 SHA256 순서와 largest-remainder 층화로 선택했으며,
  MATH500 `(subject, level)`, MMLU `subject` 층화를 유지한다. 정오답은 선택에 사용하지 않았다.
- manifest는 원본 revision, ID/선택 행 해시와 부모 cohort 해시를 기록한다.
  L40S manifest의 `Local measured capacity recommendation` 문구는 최초 동결 당시 기록이다.
  이 문서와 프로필 등록으로 **팀 공용 정본으로 채택**했으며 manifest 자체는 변경하지 않았다.
- 사람마다 같은 프로필의 같은 ID를 쓴다. 프로필 간 점수/시간은 별도 그룹으로 보고한다.
  AIME/GSM8K가 같은 문제 전체여도 cohort 및 하드웨어 정보를 섞지 않는다.
- **작업자마다 baseline을 한 번 측정해 고정하고, 이후 ours만 바꾼다.**
  다음 작업자는 자기 baseline을 먼저 측정한다. [필수 baseline 재사용 절차](BASELINE_REUSE.md).
- 2시간 목표는 첫 baseline+ours 비교를 위한 산정 기준이다. baseline을 고정한 뒤에도
  ours별로 같은 ID 수를 유지하며, 남는 시간만큼 문제를 늘리거나 다시 추첨하지 않는다.

## 실행 코드와 명령

실행 코드는 [ch-2026-11-15](https://github.com/yucheon6000/lost-token/tree/ch-2026-11-15)의
프로필/고정 baseline 지원 버전을 기반으로 개인 브랜치를 만든다.
검증 기준 실행 코드 commit은 `72061dc7`이다.
구버전 `changho-2026-11-15`의 wrapper는 `shared-v1`에 고정되어 새 옵션을 지원하지 않는다.
이 공용 허브에서 GPU 실험을 실행하지 않는다.

```bash
git fetch origin
git switch -c MYNAME-base-l40s-YYYY-MM-DD origin/ch-2026-11-15
git worktree add --detach .shared-evaluation origin/shared-evaluation
uv sync --frozen
uv run --frozen python scripts/shared_eval.py prepare --profile l40s-4gpu \
  --name MYNAME-base-l40s --date YYYY-MM-DD --work-dir workspace
uv run --frozen python scripts/shared_eval.py check --profile l40s-4gpu \
  --name MYNAME-base-l40s --date YYYY-MM-DD --work-dir workspace
uv run --frozen python scripts/shared_eval.py run --profile l40s-4gpu \
  --name MYNAME-base-l40s --date YYYY-MM-DD --work-dir workspace \
  --gpus 0,1,2,3 --arms baseline \
  --method-description '일반 AR baseline 1회 측정 및 고정' \
  --hypothesis '이 작업자의 후속 ours 실험은 동일 baseline을 참조한다'
```

`MYNAME`, `YYYY-MM-DD`를 실제 값으로 바꾼다. 실행 전 개인 코드/설정을 commit하고 CPU 테스트,
필요한 GPU 최종 답 검증을 마친다. 공유 모델 캐시가 있으면 모든 명령에 같은 `--model-cache`를 전달한다.
별도 공용 checkout은 `--shared-root /path/to/shared-checkout`으로 지정한다.

PRO 6000 8 GPU에서는 개인 브랜치/별칭을 별도로 만들고, 위 prepare/check/run 모두에서
`--profile pro6000-8gpu`, run에서 `--gpus 0,1,2,3,4,5,6,7`을 사용한다.
wrapper는 프로필의 GPU 종류/장수와 task별 batch를 확인·적용한다.
실제 사용 config는 개인 `workspace/shared-studies/<study>/task-configs/`에 보존한다.
이후 **ours-only 실행 명령**은 [BASELINE_REUSE.md](BASELINE_REUSE.md)에 있다.

## L40S 크기의 측정 근거와 한계

[실측 환경](../evaluation/measurements/l40s-2h-v1/environment.json),
[측정 요약 CSV](../evaluation/measurements/l40s-2h-v1/recommendations.csv),
[추정식/모든 가정](../evaluation/measurements/l40s-2h-v1/forecast.json),
[긴 문맥 검사](../evaluation/measurements/l40s-2h-v1/context-probe.json)를 보존했다.
각 데이터셋/방법을 최대 약 5분 관찰했고 수학 두 종은 batch=4로 추가 측정했다.
속도는 현재 L40S에서 측정했으며 과거 PRO 6000의 실행 시간을 실측처럼 사용하지 않았다.

| Dataset | GPU당 body tokens/s baseline / ours | 산정 시간, 여유 포함 |
|---|---:|---:|
| AIME25 | 179 / 125 | 약 113분 |
| HMMT25 | 179 / 116 | 약 109분 |
| GPQA Main | 205 / 147 | 약 110분 |
| MATH500 | 219 / 138 | 약 112분 |
| GSM8K | 215 / 137 | 약 116분 |
| MMLU | 221 / 138 | 약 118분 |

시간은 4 GPU 환산, 긴 문맥 비용 보정, 35% 여유와 로딩/audit용 최소 10분을 포함한 **추정**이다.
긴 수학 문제는 pilot 중 완료되지 않았으므로 동일 코드/모델의 과거 ours 출력 길이를
20% 늘려 보조로 사용했다. 일부 다른 task의 짧은 표본도 미완료 길이 모델을 사용한다.
**2시간 실행을 실제로 완료한 결과나 엄격한 상한 보장이 아니다.**
다른 ours 방법의 분기/메모리 비용이 증가하면 더 오래 걸릴 수 있다. 그래도 비교 ID는 그대로 유지한다.
32K 합성 문맥에서는 batch=8 약 30 tokens/s, batch=4 약 88 tokens/s를 관측해 수학 batch를 4로 정했다.

[pilot 정확도 원본 요약](../evaluation/measurements/l40s-2h-v1/pilot-quality.json)의 수치는 최종 고정 평가셋 전체 성능이 아니다. 빨리 끝난 공통 완료 문제만으로는
GPQA 2/3, MATH500 5/5, GSM8K 26/27, MMLU 9/11로 baseline/ours 정오답이 같았고,
AIME/HMMT는 완료 문제가 없었다. 개선 여부는 고정 ID 전체의 정식 평가로 판단한다.
