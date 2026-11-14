# Claude: 공용 가이드·결과 브랜치

여기는 `shared-evaluation` 브랜치다. [공통 가이드](docs/EXPERIMENT_GUIDE.md)를 읽는다.

1. 코드/설정/테스트 수정과 실험 실행은 개인 `{name}-{YYYY-MM-DD}` 브랜치에서 한다.
2. 먼저 [하드웨어별 필수 프로필](docs/EVALUATION_PROFILES.md)을 선택한다.
   L40S 4장 = `--profile l40s-4gpu` → `evaluation/subsets/l40s-2h-v1/`;
   RTX PRO 6000 Blackwell 8장 = `--profile pro6000-8gpu` → 기존 `evaluation/subsets/shared-v1/`.
   **같은 프로필의 모든 작업자는 이 정본 ID를 그대로 사용한다. 개인별 재추첨·`--limit` 대체 금지.**
   L40S의 AIME/HMMT batch=4, 나머지 batch=8이며 실행 wrapper가 적용한다.
   두 프로필은 별도 결과 그룹이다. 기존 PRO 6000 정본을 L40S 크기로 바꾸지 않는다.
3. [baseline 재사용 규약](docs/BASELINE_REUSE.md): 각 작업자는 `--arms baseline`으로 본인 AR baseline을 **1회** 완료/audit해 동결한다.
   이후 새 방법은 `--arms ours --baseline-ref .../baseline-reference.json`으로 **ours만** 실행한다.
   다음 작업자도 자기 baseline부터 측정한다. 고정 baseline의 hash/원본 commit과 ours별 비교를 결과에 남긴다.
4. 결과는 개인 코드 저장소의 `workspace/shared-studies/{name}-{date}/submission/`에 만든다.
5. 결과 폴더만 이 브랜치의 `experiment-results/{name}-{date}/`에 복사한다.
6. baseline.md / ours.md / method.md / environment.json / submission.json을 검토한다.
   일반 AR baseline이 없으면 미측정이라고 쓰고 다른 ours나 과거 점수로 대체하지 않는다.
7. `tools/results.py validate`와 `tools/results.py index`로 전체 비교표를 갱신한다.
8. 결과 폴더와 비교표만 commit하고 `shared-evaluation`에 push한다.
   개인 코드 브랜치 전체를 이 브랜치에 merge하지 않는다.
9. 동시에 제출돼 push가 거부되면 최신 공용 branch 위로 rebase하고 비교표를 다시 생성한다. force-push 금지.

권장 사용자 요청:

> 이름은 MYNAME이야. 공용 가이드대로 개인 코드 브랜치에서 [방법]을 구현하고,
> `--profile l40s-4gpu`의 고정 평가셋에서 내 baseline을 1회 동결하고, 이후 ours만 바꿔 비교해. GPU [목록]을 사용하고 환경도 기록해.
> 코드/설정은 내 브랜치에, 결과는 shared-evaluation에 비교표와 함께 push해.

문서·결과 정리 요청만으로 GPU 실험을 시작하지 않는다.
