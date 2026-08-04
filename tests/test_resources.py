from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from supabase_auth.types import User

from app.integrations.supabase import AuthContext, get_resource_auth_context
from app.main import create_app
from supabase import AsyncClient

BOOKMARK = {
    "id": "bookmark-1",
    "title": "Example",
    "url": "https://example.com",
    "description": None,
    "is_favorite": False,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
    "user_id": "user-123",
    "folder_id": None,
    "section_id": None,
    "position": 0,
}
FOLDER = {
    "id": "folder-1",
    "name": "Work",
    "color": None,
    "parent_id": None,
    "position": 0,
    "user_id": "user-123",
}
SECTION = {
    "id": "section-1",
    "name": "Reading",
    "color": None,
    "folder_id": "folder-1",
    "position": 0,
    "user_id": "user-123",
}


class FakeResponse:
    def __init__(self, data: object) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, owner: "FakeSupabase", table: str) -> None:
        self.owner = owner
        self.table = table
        self.action = ""
        self.columns: tuple[str, ...] = ()
        self.payload: object = None
        self.filters: list[tuple[str, object]] = []
        self.ordering: tuple[str, bool] | None = None
        self.limit_size: int | None = None

    def select(self, *columns: str) -> "FakeQuery":
        self.action = "select"
        self.columns = columns
        return self

    def insert(self, payload: object) -> "FakeQuery":
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload: object) -> "FakeQuery":
        self.action = "update"
        self.payload = payload
        return self

    def delete(self) -> "FakeQuery":
        self.action = "delete"
        return self

    def eq(self, column: str, value: object) -> "FakeQuery":
        self.filters.append((column, value))
        return self

    def neq(self, column: str, value: object) -> "FakeQuery":
        self.filters.append((f"{column}__neq", value))
        return self

    def is_(self, column: str, value: object) -> "FakeQuery":
        self.filters.append((f"{column}__is", value))
        return self

    def order(self, column: str, *, desc: bool = False) -> "FakeQuery":
        self.ordering = (column, desc)
        return self

    def limit(self, size: int) -> "FakeQuery":
        self.limit_size = size
        return self

    async def execute(self) -> FakeResponse:
        result = self.owner.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return FakeResponse(result)


class FakeSupabase:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.queries: list[FakeQuery] = []

    def table(self, name: str) -> FakeQuery:
        query = FakeQuery(self, name)
        self.queries.append(query)
        return query

    def rpc(self, name: str, params: object) -> FakeQuery:
        query = FakeQuery(self, f"rpc:{name}")
        query.action = "rpc"
        query.payload = params
        self.queries.append(query)
        return query


class FakeHttpClient:
    closed = False

    async def aclose(self) -> None:
        self.closed = True


def _user() -> User:
    return User.model_validate(
        {
            "id": "user-123",
            "email": "user@example.com",
            "app_metadata": {},
            "user_metadata": {},
            "aud": "authenticated",
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        }
    )


def _client(fake: FakeSupabase) -> TestClient:
    app: FastAPI = create_app()

    async def authenticated() -> AsyncIterator[AuthContext]:
        yield AuthContext(user=_user(), client=cast(AsyncClient, fake))

    app.dependency_overrides[get_resource_auth_context] = authenticated
    return TestClient(app)


def _assert_user_scoped(query: FakeQuery) -> None:
    assert ("user_id", "user-123") in query.filters


def test_legacy_health_alias() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_resources_require_authentication() -> None:
    response = TestClient(create_app()).get("/api/bookmarks")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_resources_accept_configured_service_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import Settings
    from app.integrations import supabase

    fake = FakeSupabase(
        [{"user_id": "user-123"}],
        [],
        [],
        [],
        [BOOKMARK],
    )
    http_client = FakeHttpClient()

    async def create_client(*_: object) -> tuple[AsyncClient, httpx.AsyncClient]:
        return cast(AsyncClient, fake), cast(httpx.AsyncClient, http_client)

    monkeypatch.setattr(supabase, "_new_client", create_client)
    settings = Settings(
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        SUPABASE_SECRET_KEY="sb_secret_test",
        BOOKMARK_API_KEY="bookmark-api-secret",
    )

    response = TestClient(create_app(settings)).get(
        "/api/bookmarks",
        headers={"X-Bookmark-Key": "bookmark-api-secret"},
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == "bookmark-1"
    _assert_user_scoped(fake.queries[-1])
    assert http_client.closed is True


def test_resources_reject_invalid_service_key() -> None:
    from app.core.config import Settings

    settings = Settings(
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        BOOKMARK_API_KEY="bookmark-api-secret",
    )

    response = TestClient(create_app(settings)).get(
        "/api/bookmarks",
        headers={"X-Bookmark-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_api_key"


@pytest.mark.parametrize(
    ("path", "table", "row"),
    [
        ("/api/bookmarks", "items", BOOKMARK),
        ("/api/folders", "folders", FOLDER),
        ("/api/sections", "sections", SECTION),
    ],
)
def test_lists_are_user_scoped(path: str, table: str, row: dict[str, Any]) -> None:
    fake = FakeSupabase([row])

    response = _client(fake).get(path, headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert fake.queries[0].table == table
    assert fake.queries[0].ordering == ("position", False)
    _assert_user_scoped(fake.queries[0])


@pytest.mark.parametrize(
    ("path", "payload", "table", "row"),
    [
        (
            "/api/bookmarks",
            {"title": "Example", "url": "https://example.com"},
            "items",
            BOOKMARK,
        ),
        ("/api/folders", {"name": "Work"}, "folders", FOLDER),
        (
            "/api/sections",
            {"name": "Reading", "folderId": "folder-1"},
            "sections",
            SECTION,
        ),
    ],
)
def test_creates_are_user_scoped(
    path: str,
    payload: dict[str, Any],
    table: str,
    row: dict[str, Any],
) -> None:
    positioned_row = {**row, "position": 3}
    fake = FakeSupabase([{"position": 2}], [positioned_row])

    response = _client(fake).post(
        path,
        json=payload,
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 201
    assert fake.queries[0].table == table
    assert fake.queries[0].ordering == ("position", True)
    assert fake.queries[0].limit_size == 1
    _assert_user_scoped(fake.queries[0])
    assert isinstance(fake.queries[1].payload, dict)
    assert fake.queries[1].payload["user_id"] == "user-123"
    assert fake.queries[1].payload["position"] == 3


def test_folder_creation_preserves_color() -> None:
    folder = {**FOLDER, "color": "#123456"}
    fake = FakeSupabase([], [folder])

    response = _client(fake).post(
        "/api/folders",
        json={"name": "Work", "color": "#123456"},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 201
    assert isinstance(fake.queries[1].payload, dict)
    assert fake.queries[1].payload["color"] == "#123456"


def test_section_creation_preserves_color() -> None:
    section = {**SECTION, "color": "#db2777"}
    fake = FakeSupabase([], [section])

    response = _client(fake).post(
        "/api/sections",
        json={"name": "Reading", "folderId": "folder-1", "color": "#db2777"},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 201
    assert response.json()["color"] == "#db2777"
    assert isinstance(fake.queries[1].payload, dict)
    assert fake.queries[1].payload["color"] == "#db2777"


def test_folder_creation_scopes_position_to_its_parent() -> None:
    child = {**FOLDER, "id": "folder-2", "parent_id": "folder-1"}
    fake = FakeSupabase([FOLDER], [], [child])

    response = _client(fake).post(
        "/api/folders",
        json={"name": "Child", "parentId": "folder-1"},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 201
    assert fake.queries[0].table == "folders"
    _assert_user_scoped(fake.queries[0])
    assert ("parent_id", "folder-1") in fake.queries[1].filters
    assert isinstance(fake.queries[2].payload, dict)
    assert fake.queries[2].payload["parent_id"] == "folder-1"


def test_folder_move_rejects_a_descendant_as_parent() -> None:
    child = {**FOLDER, "id": "folder-2", "parent_id": "folder-1"}
    fake = FakeSupabase([FOLDER, child])

    response = _client(fake).patch(
        "/api/folders/folder-1",
        json={"parentId": "folder-2"},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "folder_parent_invalid"
    assert len(fake.queries) == 1
    _assert_user_scoped(fake.queries[0])


def test_folder_tree_returns_nested_nodes_from_flat_folders() -> None:
    child = {**FOLDER, "id": "folder-2", "name": "Child", "parent_id": "folder-1"}
    fake = FakeSupabase([child, FOLDER])

    response = _client(fake).get(
        "/api/folders/tree",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "folder-1",
            "name": "Work",
            "color": None,
            "parentId": None,
            "position": 0,
            "userId": "user-123",
            "children": [
                {
                    "id": "folder-2",
                    "name": "Child",
                    "color": None,
                    "parentId": "folder-1",
                    "position": 0,
                    "userId": "user-123",
                    "children": [],
                }
            ],
        }
    ]
    _assert_user_scoped(fake.queries[0])


@pytest.mark.parametrize(
    ("path", "payload", "table", "row"),
    [
        (
            "/api/bookmarks/bookmark-1",
            {"title": "Updated"},
            "items",
            {**BOOKMARK, "title": "Updated"},
        ),
        (
            "/api/folders/folder-1",
            {"name": "Updated"},
            "folders",
            {**FOLDER, "name": "Updated"},
        ),
        (
            "/api/sections/section-1",
            {"name": "Updated"},
            "sections",
            {**SECTION, "name": "Updated"},
        ),
    ],
)
def test_updates_are_user_scoped(
    path: str,
    payload: dict[str, Any],
    table: str,
    row: dict[str, Any],
) -> None:
    fake = FakeSupabase([row])

    response = _client(fake).patch(
        path,
        json=payload,
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert fake.queries[0].table == table
    assert ("id", path.rsplit("/", 1)[-1]) in fake.queries[0].filters
    _assert_user_scoped(fake.queries[0])


@pytest.mark.parametrize("color", ["#2166d7", None])
def test_section_update_preserves_color(color: str | None) -> None:
    section = {**SECTION, "color": color}
    fake = FakeSupabase([section])

    response = _client(fake).patch(
        "/api/sections/section-1",
        json={"color": color},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json()["color"] == color
    assert fake.queries[0].payload["color"] == color


def test_section_list_returns_color() -> None:
    section = {**SECTION, "color": "#16a34a"}
    fake = FakeSupabase([section])

    response = _client(fake).get(
        "/api/sections",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "section-1",
            "name": "Reading",
            "color": "#16a34a",
            "folderId": "folder-1",
            "position": 0,
            "userId": "user-123",
        }
    ]


@pytest.mark.parametrize(
    ("path", "table"),
    [
        ("/api/bookmarks/bookmark-1", "items"),
        ("/api/sections/section-1", "sections"),
    ],
)
def test_deletes_are_user_scoped(path: str, table: str) -> None:
    fake = FakeSupabase([{"id": path.rsplit("/", 1)[-1]}])

    response = _client(fake).delete(
        path,
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 204
    assert fake.queries[0].table == table
    _assert_user_scoped(fake.queries[0])


def test_folder_delete_uses_atomic_destination_rpc() -> None:
    fake = FakeSupabase([{"id": "folder-1"}])

    response = _client(fake).delete(
        "/api/folders/folder-1?destination_folder_id=folder-2",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 204
    assert fake.queries[0].table == "rpc:delete_folder"
    assert fake.queries[0].payload == {
        "p_folder_id": "folder-1",
        "p_destination_folder_id": "folder-2",
        "p_user_id": "user-123",
    }


def test_folder_delete_rejects_itself_as_destination() -> None:
    fake = FakeSupabase()

    response = _client(fake).delete(
        "/api/folders/folder-1?destination_folder_id=folder-1",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "folder_destination_invalid"
    assert fake.queries == []


@pytest.mark.parametrize(
    ("path", "table"),
    [
        ("/api/bookmarks/reorder", "items"),
        ("/api/folders/reorder", "folders"),
        ("/api/sections/reorder", "sections"),
    ],
)
def test_reorders_are_user_scoped(path: str, table: str) -> None:
    fake = FakeSupabase([{"id": "one"}], [{"id": "two"}])

    response = _client(fake).post(
        path,
        json=[{"id": "one", "position": 1}, {"id": "two", "position": 2}],
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 204
    assert [query.table for query in fake.queries] == [table, table]
    assert all(("user_id", "user-123") in query.filters for query in fake.queries)


def test_missing_resource_uses_stable_404() -> None:
    response = _client(FakeSupabase([])).delete(
        "/api/bookmarks/missing",
        headers={"Authorization": "Bearer test", "X-Request-ID": "req-missing"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "code": "resource_not_found",
        "message": "Bookmark not found",
        "request_id": "req-missing",
    }


@pytest.mark.parametrize(
    ("failure", "status_code", "code"),
    [
        (
            APIError(
                {
                    "code": "42501",
                    "message": "permission denied",
                    "details": None,
                    "hint": None,
                }
            ),
            403,
            "database_access_denied",
        ),
        (
            APIError(
                {
                    "code": "PGRST000",
                    "message": "internal details",
                    "details": None,
                    "hint": None,
                }
            ),
            502,
            "database_request_failed",
        ),
        (httpx.ConnectError("private upstream detail"), 503, "database_unavailable"),
    ],
)
def test_database_failures_are_sanitized(
    failure: Exception, status_code: int, code: str
) -> None:
    response = _client(FakeSupabase(failure)).get(
        "/api/bookmarks",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert str(failure) not in response.text


def test_invalid_database_payload_is_sanitized() -> None:
    response = _client(FakeSupabase({"not": "a list"})).get(
        "/api/bookmarks",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 502
    assert response.json()["code"] == "database_response_invalid"


def test_graphql_lists_share_the_rest_data_and_user_scope() -> None:
    section = {**SECTION, "color": "#16a34a"}
    fake = FakeSupabase([BOOKMARK], [FOLDER], [section])

    response = _client(fake).post(
        "/graphql",
        json={
            "query": """
                {
                  bookmarks {
                    id title url description isFavorite folderId sectionId position
                  }
                  folders { id name color position }
                  sections { id name color folderId position }
                }
            """
        },
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "bookmarks": [
                {
                    "id": "bookmark-1",
                    "title": "Example",
                    "url": "https://example.com",
                    "description": None,
                    "isFavorite": False,
                    "folderId": None,
                    "sectionId": None,
                    "position": 0,
                }
            ],
            "folders": [
                {
                    "id": "folder-1",
                    "name": "Work",
                    "color": None,
                    "position": 0,
                }
            ],
            "sections": [
                {
                    "id": "section-1",
                    "name": "Reading",
                    "color": "#16a34a",
                    "folderId": "folder-1",
                    "position": 0,
                }
            ],
        }
    }
    assert [query.table for query in fake.queries] == [
        "items",
        "folders",
        "sections",
    ]
    assert all(("user_id", "user-123") in query.filters for query in fake.queries)


def test_graphql_bookmark_mutations_share_rest_crud_and_user_scope() -> None:
    created = {**BOOKMARK, "position": 3}
    updated = {**created, "title": "Updated"}
    fake = FakeSupabase(
        [{"position": 2}],
        [created],
        [updated],
        [{"id": "bookmark-1"}],
        [{"id": "bookmark-1"}],
    )

    response = _client(fake).post(
        "/graphql",
        json={
            "query": """
                mutation BookmarkCrud($id: ID!) {
                  created: createBookmark(input: {
                    title: "Example"
                    url: "https://example.com"
                    isFavorite: false
                  }) { id title position }
                  updated: updateBookmark(
                    id: $id
                    input: { title: "Updated" }
                  ) { id title }
                  deleted: deleteBookmark(id: $id)
                  reordered: reorderBookmarks(
                    input: [{ id: "bookmark-1", position: 4 }]
                  )
                }
            """,
            "variables": {"id": "bookmark-1"},
        },
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "created": {
                "id": "bookmark-1",
                "title": "Example",
                "position": 3,
            },
            "updated": {"id": "bookmark-1", "title": "Updated"},
            "deleted": True,
            "reordered": True,
        }
    }
    assert fake.queries[0].ordering == ("position", True)
    assert fake.queries[1].payload["user_id"] == "user-123"
    assert all(("user_id", "user-123") in query.filters for query in fake.queries[2:])


def test_graphql_folder_and_section_mutations_share_rest_crud() -> None:
    updated_folder = {**FOLDER, "name": "Updated"}
    created_section = {**SECTION, "color": "#db2777"}
    updated_section = {
        **SECTION,
        "name": "Updated section",
        "color": "#2166d7",
    }
    fake = FakeSupabase(
        [],
        [FOLDER],
        [updated_folder],
        [{"id": "folder-1"}],
        [{"id": "folder-1"}],
        [],
        [created_section],
        [updated_section],
        [{"id": "section-1"}],
        [{"id": "section-1"}],
    )

    response = _client(fake).post(
        "/graphql",
        json={
            "query": """
                mutation {
                  createdFolder: createFolder(
                    input: { name: "Work", color: null }
                  ) { id name color position }
                  updatedFolder: updateFolder(
                    id: "folder-1"
                    input: { name: "Updated" }
                  ) { id name }
                  deletedFolder: deleteFolder(id: "folder-1")
                  reorderedFolders: reorderFolders(
                    input: [{ id: "folder-1", position: 1 }]
                  )
                  createdSection: createSection(
                    input: {
                      folderId: "folder-1"
                      name: "Reading"
                      color: "#db2777"
                    }
                  ) { id name color folderId position }
                  updatedSection: updateSection(
                    id: "section-1"
                    input: { name: "Updated section", color: "#2166d7" }
                  ) { id name color }
                  deletedSection: deleteSection(id: "section-1")
                  reorderedSections: reorderSections(
                    input: [{ id: "section-1", position: 2 }]
                  )
                }
            """
        },
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "createdFolder": {
                "id": "folder-1",
                "name": "Work",
                "color": None,
                "position": 0,
            },
            "updatedFolder": {"id": "folder-1", "name": "Updated"},
            "deletedFolder": True,
            "reorderedFolders": True,
            "createdSection": {
                "id": "section-1",
                "name": "Reading",
                "color": "#db2777",
                "folderId": "folder-1",
                "position": 0,
            },
            "updatedSection": {
                "id": "section-1",
                "name": "Updated section",
                "color": "#2166d7",
            },
            "deletedSection": True,
            "reorderedSections": True,
        }
    }
    assert fake.queries[5].filters == [
        ("user_id", "user-123"),
        ("folder_id", "folder-1"),
    ]
    assert fake.queries[6].payload["user_id"] == "user-123"
    assert fake.queries[6].payload["color"] == "#db2777"
    assert fake.queries[7].payload["name"] == "Updated section"
    assert fake.queries[7].payload["color"] == "#2166d7"
    _assert_user_scoped(fake.queries[7])


def test_graphql_folder_hierarchy_fields_share_rest_contract() -> None:
    child = {**FOLDER, "id": "folder-2", "name": "Child", "parent_id": "folder-1"}
    fake = FakeSupabase([FOLDER], [], [child], [{"id": "folder-2"}])

    response = _client(fake).post(
        "/graphql",
        json={
            "query": """
                mutation {
                  created: createFolder(input: {
                    name: "Child"
                    parentId: "folder-1"
                  }) { id parentId position }
                  deleted: deleteFolder(
                    id: "folder-2"
                    destinationFolderId: "folder-1"
                  )
                }
            """
        },
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "created": {"id": "folder-2", "parentId": "folder-1", "position": 0},
            "deleted": True,
        }
    }
    assert ("parent_id", "folder-1") in fake.queries[1].filters
    assert fake.queries[3].payload == {
        "p_folder_id": "folder-2",
        "p_destination_folder_id": "folder-1",
        "p_user_id": "user-123",
    }


def test_graphql_maps_missing_rows_to_not_found() -> None:
    response = _client(FakeSupabase([])).post(
        "/graphql",
        json={
            "query": """
                mutation {
                  deleteBookmark(id: "missing")
                }
            """
        },
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    error = response.json()["errors"][0]
    assert {
        "message": error["message"],
        "path": error["path"],
        "extensions": error["extensions"],
    } == {
        "message": "Bookmark not found",
        "path": ["deleteBookmark"],
        "extensions": {"code": "NOT_FOUND"},
    }


def test_graphql_accepts_the_same_service_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import Settings
    from app.integrations import supabase

    fake = FakeSupabase(
        [{"user_id": "user-123"}],
        [],
        [],
        [],
        [BOOKMARK],
    )
    http_client = FakeHttpClient()

    async def create_client(*_: object) -> tuple[AsyncClient, httpx.AsyncClient]:
        return cast(AsyncClient, fake), cast(httpx.AsyncClient, http_client)

    monkeypatch.setattr(supabase, "_new_client", create_client)
    settings = Settings(
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        SUPABASE_SECRET_KEY="sb_secret_test",
        BOOKMARK_API_KEY="bookmark-api-secret",
    )

    response = TestClient(create_app(settings)).post(
        "/graphql",
        json={"query": "{ bookmarks { id } }"},
        headers={"X-Bookmark-Key": "bookmark-api-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"data": {"bookmarks": [{"id": "bookmark-1"}]}}
    _assert_user_scoped(fake.queries[-1])
    assert http_client.closed is True
