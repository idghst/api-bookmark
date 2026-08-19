# fastapi-bookmark

`bookmark` Supabase schema를 사용하는 FastAPI 서비스입니다. 테이블은
`items`, `folders`, `sections`입니다.

- Vercel Python Function
- Supabase Auth JWT 또는 서버 간 `X-Bookmark-Key`
- JSON 오류 응답과 request ID
- Ruff, mypy, pytest coverage 90%, pip-audit CI

## 보안 구조

`/api/bookmarks`, `/api/folders`, `/api/sections` 요청은 사용자용
`Authorization: Bearer <Supabase access token>` 또는 개인 Next.js 서버용
`X-Bookmark-Key`를 요구합니다. `X-Bookmark-Key` 요청은
`SUPABASE_SECRET_KEY` 관리자 클라이언트로 기존 데이터의 유일한 `user_id`
소유자를 자동 선택하고 같은 소유자 조건으로 제한합니다. 데이터가 비어 있거나
소유자가 둘 이상이면 서비스 요청을 거부합니다.

환경은 요청 Host/URL hostname으로만 가릅니다. `test`면 test, `dev` 또는
localhost/127.0.0.1이면 development, 그 외는 production입니다. production host에서는
`/docs` `/redoc` `/openapi.json`을 비공개합니다. 로그 레벨은 INFO JSON으로
고정입니다.

## Local development

Python 3.12와 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
uv sync --locked --dev
```

`.env.example`을 `.env.local`로 복사한 뒤 실제 키를 넣으세요. 실제 키는 절대
커밋하지 마세요.

```bash
uv run uvicorn app.main:app --reload
```

- API: <http://127.0.0.1:8000>
- Docs (localhost / Host에 `dev` 또는 `test`): <http://127.0.0.1:8000/docs>
- Liveness: <http://127.0.0.1:8000/health/live>
- Readiness: <http://127.0.0.1:8000/health/ready>

환경 변수는 아래만 사용합니다.

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your_publishable_key
SUPABASE_SECRET_KEY=
BOOKMARK_API_KEY=
```

`CORS_ORIGINS`는 `http://localhost:3000`으로 고정입니다. production host에서는
`SUPABASE_URL`이 HTTPS여야 합니다. 서버 간 호출을 쓰면 `BOOKMARK_API_KEY`와
`SUPABASE_SECRET_KEY`를 설정하고 `X-Bookmark-Key`만 전달합니다.

## API

상태와 인증:

- `GET /`
- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/auth/me`

Bookmarks (`bookmark.items`):

- `GET /api/bookmarks`
- `POST /api/bookmarks`
- `PATCH /api/bookmarks/{bookmark_id}`
- `DELETE /api/bookmarks/{bookmark_id}`
- `POST /api/bookmarks/reorder`

Folders (`bookmark.folders`):

- `GET /api/folders`
- `POST /api/folders`
- `PATCH /api/folders/{folder_id}`
- `DELETE /api/folders/{folder_id}`
- `POST /api/folders/reorder`

Sections (`bookmark.sections`):

- `GET /api/sections`
- `POST /api/sections`
- `PATCH /api/sections/{section_id}`
- `DELETE /api/sections/{section_id}`
- `POST /api/sections/reorder`

응답 필드는 camelCase입니다 (`isFavorite`, `color`, `folderId`, `sectionId`,
`createdAt`, `updatedAt`, `userId`). `sectionId`는 폴더에서만 사용하며 북마크는
`folderId`로 폴더에 속합니다.

## Supabase

각 서비스는 독립 Supabase project를 사용합니다. 이 프로젝트는 고정
`bookmark` schema만 조회합니다.

```bash
npx --yes supabase@latest login
npx --yes supabase@latest link --project-ref <project-ref>
npx --yes supabase@latest db push
```

Supabase Dashboard의 `API Settings > Exposed schemas`에 `bookmark`를
추가해야 합니다. 마이그레이션은 schema, `items`, `folders`, `sections`,
인덱스, grants, RLS policy를 관리합니다.

운영 DB에 적용하기 전:

```bash
npx --yes supabase@latest db lint --linked
npx --yes supabase@latest db diff --linked
```

## 호출 예시

```bash
curl \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "X-Request-ID: local-check-1" \
  http://localhost:8000/api/bookmarks
```

```bash
curl \
  -H "X-Bookmark-Key: $BOOKMARK_API_KEY" \
  http://localhost:8000/api/bookmarks
```

오류 응답:

```json
{
  "code": "invalid_access_token",
  "message": "Invalid access token",
  "request_id": "local-check-1"
}
```

## 검증

```bash
uv lock --check
uv run ruff format --check app tests
uv run ruff check --no-cache app tests
uv run mypy app
uv run pytest -m "not integration" --cov=app --cov-report=term-missing
uv run pip-audit
python -m json.tool vercel.json >/dev/null
```

실제 Supabase 검증은 아래 값을 별도 test 환경에 설정한 뒤 실행합니다.

```bash
SUPABASE_TEST_ACCESS_TOKEN=... \
uv run pytest -m integration -v
```

자격 증명이 없으면 integration test는 명확한 사유와 함께 skip됩니다.

## Vercel

Vercel project: `idghst/api-bookmark`

Preview와 Production에 각각 환경 변수를 설정합니다.

```bash
npx --yes vercel@57 link --yes --scope idghst --project api-bookmark
npx --yes vercel@57 env add SUPABASE_URL preview production
npx --yes vercel@57 env add SUPABASE_PUBLISHABLE_KEY preview production
```

배포는 CI 통과 후 source deployment로 수행합니다.

```bash
vercel build --target=preview
vercel deploy --target=preview
npx --yes vercel@57 inspect <preview-url>
```

Preview에서 `/health/live`, `/health/ready`, invalid-token `401`, 실제 token
CRUD와 사용자 간 RLS 격리를 확인한 뒤 Production으로 승격합니다.

```bash
npx --yes vercel@57 promote <preview-url>
```

문제 발생 시 response의 `X-Request-ID`로 Vercel runtime logs를 조회합니다.
키나 JWT 원문은 로그, issue, 커밋에 남기지 않습니다.
