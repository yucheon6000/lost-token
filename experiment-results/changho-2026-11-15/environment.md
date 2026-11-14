# 실행 환경

12개 run 모두 GPU **8장**을 사용했다. GPU별 독립 worker/model 구성이다.

| 항목 | 기록 |
|---|---|
| GPU 모델 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| 사용 장수 / physical 번호 | **8장 / 0,1,2,3,4,5,6,7** |
| 장당 VRAM | 97,887 MiB (사후 inventory) |
| 모델 정밀도 | BF16 |
| 엔진 | vLLM 0.10.2 V0, prefix caching, CUDA graphs |
| Tensor parallel / worker 수 | TP=1 / GPU worker 8 |
| GPU당 최대 동시 case | 8 (작은 데이터셋은 실제 shard 수에 따라 더 적음) |
| max batched tokens / memory fraction | 4,096 / 0.85 |
| Python | 3.12.3 |
| PyTorch / CUDA runtime | 2.8.0 / 12.8 |
| Transformers / Tokenizers | 4.57.1 / 0.22.2 |
| Hugging Face Hub / NumPy | 0.36.2 / 2.2.6 |
| OS (실행 identity) | Linux-7.0.0-34-generic-x86_64-with-glibc2.39 |
| NVIDIA driver | 610.57.04 (**2026-11-15 사후 관측**) |
| Host CPU / RAM | logical CPU 256 / 약 755.4 GiB (**사후 관측**) |

[environment.json](environment.json)의 `recorded_during_runs`는 실행 당시 worker identity에서
추출한 GPU 번호/모델/패키지/runtime과 identity hash를 포함한다.
`observed_after_runs`는 나중에 수집한 GPU UUID/드라이버/host inventory다.
사후 관측값을 과거 실행 시작 시점에 수집한 것으로 주장하지 않는다.

원본 환경/모델/체크포인트는 Git에 업로드하지 않았으며, 재현 설정과 검증용 해시를 보존했다.
