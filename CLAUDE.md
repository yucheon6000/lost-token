# Claude: 공용 가이드·결과 브랜치

여기는 `shared-evaluation` 브랜치다. [공통 가이드](docs/EXPERIMENT_GUIDE.md)를 읽는다.

1. 코드/설정/테스트 수정과 실험 실행은 개인 `{name}-{YYYY-MM-DD}` 브랜치에서 한다.
2. 고정 subset 정본은 이 브랜치의 `evaluation/subsets/shared-v1/`다. 개인별 재추첨 금지.
3. 결과는 개인 코드 저장소의 `workspace/shared-studies/{name}-{date}/submission/`에 만든다.
4. 결과 폴더만 이 브랜치의 `experiment-results/{name}-{date}/`에 복사한다.
5. baseline.md / ours.md / method.md / environment.json / submission.json을 검토한다.
   일반 AR baseline이 없으면 미측정이라고 쓰고 다른 ours나 과거 점수로 대체하지 않는다.
6. `tools/results.py validate`와 `tools/results.py index`로 전체 비교표를 갱신한다.
7. 결과 폴더와 비교표만 commit하고 `shared-evaluation`에 push한다.
   개인 코드 브랜치 전체를 이 브랜치에 merge하지 않는다.
8. 동시에 제출돼 push가 거부되면 최신 공용 branch 위로 rebase하고 비교표를 다시 생성한다. force-push 금지.

권장 사용자 요청:

> 이름은 MYNAME이야. 공용 가이드대로 개인 코드 브랜치에서 [방법]을 구현하고,
> 고정 평가셋에서 baseline/ours를 측정해. GPU [목록]을 사용하고 환경도 기록해.
> 코드/설정은 내 브랜치에, 결과는 shared-evaluation에 비교표와 함께 push해.

문서·결과 정리 요청만으로 GPU 실험을 시작하지 않는다.
