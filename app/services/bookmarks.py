from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from postgrest.exceptions import APIError

from app.core.errors import ApiError
from app.integrations.supabase import AuthContext
from app.schemas import (
    BookmarkCreate,
    BookmarkOut,
    BookmarkUpdate,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    PositionUpdate,
    SectionCreate,
    SectionOut,
    SectionUpdate,
)

TABLES = {
    "bookmarks": "items",
    "folders": "folders",
    "sections": "sections",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def _execute(query: Any) -> list[dict[str, Any]]:
    try:
        response = await query.execute()
    except APIError as error:
        if error.code == "42501":
            raise ApiError(
                403,
                "database_access_denied",
                "Database access was denied",
            ) from error
        raise ApiError(
            502,
            "database_request_failed",
            "Database request failed",
        ) from error
    except httpx.HTTPError as error:
        raise ApiError(
            503,
            "database_unavailable",
            "Database is unavailable",
        ) from error

    data = response.data
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ApiError(
            502,
            "database_response_invalid",
            "Database returned an invalid response",
        )
    return data


def _ensure_row(
    rows: list[dict[str, Any]],
    resource_name: str,
) -> dict[str, Any]:
    if not rows:
        raise ApiError(
            404,
            "resource_not_found",
            f"{resource_name} not found",
        )
    return rows[0]


async def _next_position(
    auth: AuthContext,
    table: str,
    **filters: object,
) -> int:
    query = auth.client.table(table).select("position").eq("user_id", auth.user.id)
    for column, value in filters.items():
        query = query.eq(column, value)
    rows = await _execute(query.order("position", desc=True).limit(1))
    if not rows:
        return 0
    position = rows[0].get("position")
    return (
        position + 1
        if isinstance(position, int) and not isinstance(position, bool)
        else 0
    )


async def list_bookmarks(auth: AuthContext) -> list[BookmarkOut]:
    rows = await _execute(
        auth.client.table(TABLES["bookmarks"])
        .select("*")
        .eq("user_id", auth.user.id)
        .order("position")
    )
    return [BookmarkOut(**row) for row in rows]


async def create_bookmark(
    payload: BookmarkCreate,
    auth: AuthContext,
) -> BookmarkOut:
    now = _now()
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "title": payload.title,
        "url": payload.url,
        "description": payload.description,
        "is_favorite": payload.is_favorite,
        "folder_id": payload.folder_id,
        "section_id": payload.section_id,
        "position": await _next_position(auth, TABLES["bookmarks"]),
        "created_at": now,
        "updated_at": now,
        "user_id": auth.user.id,
    }
    rows = await _execute(
        auth.client.table(TABLES["bookmarks"]).insert(row).select("*")
    )
    return BookmarkOut(**_ensure_row(rows, "Bookmark"))


async def update_bookmark(
    bookmark_id: str,
    payload: BookmarkUpdate,
    auth: AuthContext,
) -> BookmarkOut:
    updates = payload.model_dump(by_alias=False, exclude_unset=True)
    updates["updated_at"] = _now()
    rows = await _execute(
        auth.client.table(TABLES["bookmarks"])
        .update(updates)
        .eq("id", bookmark_id)
        .eq("user_id", auth.user.id)
        .select("*")
    )
    return BookmarkOut(**_ensure_row(rows, "Bookmark"))


async def delete_bookmark(bookmark_id: str, auth: AuthContext) -> None:
    rows = await _execute(
        auth.client.table(TABLES["bookmarks"])
        .delete()
        .eq("id", bookmark_id)
        .eq("user_id", auth.user.id)
        .select("id")
    )
    _ensure_row(rows, "Bookmark")


async def reorder_bookmarks(
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    await _reorder(TABLES["bookmarks"], payload, auth)


async def list_folders(auth: AuthContext) -> list[FolderOut]:
    rows = await _execute(
        auth.client.table(TABLES["folders"])
        .select("*")
        .eq("user_id", auth.user.id)
        .order("position")
    )
    return [FolderOut(**row) for row in rows]


async def create_folder(
    payload: FolderCreate,
    auth: AuthContext,
) -> FolderOut:
    now = _now()
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "name": payload.name,
        "color": payload.color,
        "position": await _next_position(auth, TABLES["folders"]),
        "created_at": now,
        "updated_at": now,
        "user_id": auth.user.id,
    }
    rows = await _execute(auth.client.table(TABLES["folders"]).insert(row).select("*"))
    return FolderOut(**_ensure_row(rows, "Folder"))


async def update_folder(
    folder_id: str,
    payload: FolderUpdate,
    auth: AuthContext,
) -> FolderOut:
    updates = payload.model_dump(exclude_unset=True)
    updates["updated_at"] = _now()
    rows = await _execute(
        auth.client.table(TABLES["folders"])
        .update(updates)
        .eq("id", folder_id)
        .eq("user_id", auth.user.id)
        .select("*")
    )
    return FolderOut(**_ensure_row(rows, "Folder"))


async def delete_folder(folder_id: str, auth: AuthContext) -> None:
    rows = await _execute(
        auth.client.table(TABLES["folders"])
        .delete()
        .eq("id", folder_id)
        .eq("user_id", auth.user.id)
        .select("id")
    )
    _ensure_row(rows, "Folder")


async def reorder_folders(
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    await _reorder(TABLES["folders"], payload, auth)


async def list_sections(auth: AuthContext) -> list[SectionOut]:
    rows = await _execute(
        auth.client.table(TABLES["sections"])
        .select("*")
        .eq("user_id", auth.user.id)
        .order("position")
    )
    return [SectionOut(**row) for row in rows]


async def create_section(
    payload: SectionCreate,
    auth: AuthContext,
) -> SectionOut:
    now = _now()
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "name": payload.name,
        "folder_id": payload.folder_id,
        "position": await _next_position(
            auth,
            TABLES["sections"],
            folder_id=payload.folder_id,
        ),
        "created_at": now,
        "updated_at": now,
        "user_id": auth.user.id,
    }
    rows = await _execute(auth.client.table(TABLES["sections"]).insert(row).select("*"))
    return SectionOut(**_ensure_row(rows, "Section"))


async def update_section(
    section_id: str,
    payload: SectionUpdate,
    auth: AuthContext,
) -> SectionOut:
    updates = payload.model_dump(exclude_unset=True)
    updates["updated_at"] = _now()
    rows = await _execute(
        auth.client.table(TABLES["sections"])
        .update(updates)
        .eq("id", section_id)
        .eq("user_id", auth.user.id)
        .select("*")
    )
    return SectionOut(**_ensure_row(rows, "Section"))


async def delete_section(section_id: str, auth: AuthContext) -> None:
    rows = await _execute(
        auth.client.table(TABLES["sections"])
        .delete()
        .eq("id", section_id)
        .eq("user_id", auth.user.id)
        .select("id")
    )
    _ensure_row(rows, "Section")


async def reorder_sections(
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    await _reorder(TABLES["sections"], payload, auth)


async def _reorder(
    table: str,
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    now = _now()
    for item in payload:
        await _execute(
            auth.client.table(table)
            .update({"position": item.position, "updated_at": now})
            .eq("id", item.id)
            .eq("user_id", auth.user.id)
            .select("id")
        )
