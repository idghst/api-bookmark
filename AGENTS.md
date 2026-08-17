# Project Agent Instructions

[work]
- 사용자 요청 범위의 수정과 검증이 끝나면, 금지 지시가 없는 한 즉시 `git-commit-push-korean` skill을 적용해 이 세션이 수정한 파일만 한글 커밋·안전 푸시한다. 대상이 혼재했거나 push 복구가 필요하면 사용자에게 보고한다.

[graphify]
- 코드 탐색 전에 `graphify query "<질문>"`, `graphify path "<A>" "<B>"`, `graphify explain "<심볼>"`을 먼저 실행한다. 서브에이전트 프롬프트에도 이 규칙을 넣는다.
- 커뮤니티 의미와 런타임 경로는 `docs/graphify/README.md`를 본다. `GRAPH_REPORT.md`의 Community N 라벨은 코드 전용 추출이라 이름이 없다.
- FastAPI `Depends`는 호출 엣지가 아닐 수 있다. directed path가 없으면 `--undirected`를 치고, 그래도 비면 문서를 따른다.
- 코드 구조가 바뀌면 `graphify update .`로 AST 그래프를 갱신한다. `graphify-out/cache/`는 커밋하지 않는다.
