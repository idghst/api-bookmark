# API 구조 리팩터 설계

## 목표

공개 REST/GraphQL 계약과 동작을 유지한 채, 한 파일에 모인 도메인·GraphQL·라우트를 엔티티 단위로 나눈다.

## 범위

포함: `app/services/`, `app/graphql/`, `app/api/routes/` 분리와 기존 경로 shim.

제외: 인증/설정 로직 변경, 마이그레이션 수정, 모바일 소비자 변경, 오류 코드·경로·필드 alias 변경.

## 목표 구조

```text
app/services/db.py          # PostgREST 실행, position, reorder
app/services/bookmarks.py   # items CRUD
app/services/folders.py     # folders CRUD + tree + RPC
app/services/sections.py    # sections CRUD + move RPC
app/graphql/                # context, types, inputs, errors, schema
app/graphql_api.py          # graphql_router shim
app/api/routes/bookmarks.py
app/api/routes/folders.py
app/api/routes/sections.py
app/api/routes/resources.py # 세 라우터 조립
```

## 계약 (변경 금지)

REST 경로와 상태 코드, GraphQL 이름, `{code,message,request_id}`, camelCase alias, `X-Bookmark-Key`, RPC 파라미터.

## 검증

`uv run ruff format --check app tests` / `ruff check` / `mypy app` / `pytest -m "not integration" --cov=app`
