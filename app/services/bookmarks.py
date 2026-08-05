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
    FolderTreeOut,
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
        if error.code == "P0002":
            raise ApiError(404, "resource_not_found", "Resource not found") from error
        if error.code in {"23503", "23514"}:
            raise ApiError(
                409,
                "resource_conflict",
                "Resource conflicts with the current folder structure",
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
        query = query.is_(column, "null") if value is None else query.eq(column, value)
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
    folders = [FolderOut(**row) for row in rows]
    return sorted(
        folders,
        key=lambda folder: (
            folder.parent_id is not None,
            folder.parent_id or "",
            folder.position,
            folder.id,
        ),
    )


async def _folder_parent_map(auth: AuthContext) -> dict[str, str | None]:
    rows = await _execute(
        auth.client.table(TABLES["folders"])
        .select("id,parent_id")
        .eq("user_id", auth.user.id)
    )
    parents: dict[str, str | None] = {}
    for row in rows:
        folder_id = row.get("id")
        parent_id = row.get("parent_id")
        if isinstance(folder_id, str) and (
            parent_id is None or isinstance(parent_id, str)
        ):
            parents[folder_id] = parent_id
    return parents


def _validate_folder_parent(
    folder_id: str | None,
    parent_id: str | None,
    parents: dict[str, str | None],
) -> None:
    if folder_id is not None and folder_id not in parents:
        raise ApiError(404, "resource_not_found", "Folder not found")
    if parent_id is None:
        return
    if folder_id == parent_id:
        raise ApiError(
            422,
            "folder_parent_invalid",
            "A folder cannot be its own parent",
        )
    if parent_id not in parents:
        raise ApiError(404, "resource_not_found", "Parent folder not found")

    current_id: str | None = parent_id
    seen: set[str] = set()
    while current_id is not None:
        if current_id == folder_id:
            raise ApiError(
                422,
                "folder_parent_invalid",
                "A folder cannot be moved into its descendant",
            )
        if current_id in seen:
            raise ApiError(
                409,
                "resource_conflict",
                "Folder structure contains a cycle",
            )
        seen.add(current_id)
        current_id = parents.get(current_id)


async def list_folder_tree(auth: AuthContext) -> list[FolderTreeOut]:
    folders = await list_folders(auth)
    folder_by_id = {folder.id: folder for folder in folders}
    children_by_parent: dict[str, list[FolderOut]] = {}
    roots: list[FolderOut] = []

    for folder in folders:
        if folder.parent_id is None or folder.parent_id not in folder_by_id:
            roots.append(folder)
        else:
            children_by_parent.setdefault(folder.parent_id, []).append(folder)

    for children in children_by_parent.values():
        children.sort(key=lambda folder: (folder.position, folder.id))
    roots.sort(key=lambda folder: (folder.position, folder.id))

    rendered: set[str] = set()

    def build(folder: FolderOut, ancestors: set[str]) -> FolderTreeOut:
        rendered.add(folder.id)
        node = FolderTreeOut(**folder.model_dump())
        next_ancestors = ancestors | {folder.id}
        node.children = [
            build(child, next_ancestors)
            for child in children_by_parent.get(folder.id, [])
            if child.id not in next_ancestors
        ]
        return node

    tree = [build(folder, set()) for folder in roots]
    for folder in folders:
        if folder.id not in rendered:
            tree.append(build(folder, set()))
    return tree


async def create_folder(
    payload: FolderCreate,
    auth: AuthContext,
) -> FolderOut:
    if payload.parent_id is not None:
        _validate_folder_parent(
            None,
            payload.parent_id,
            await _folder_parent_map(auth),
        )
    now = _now()
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "name": payload.name,
        "color": payload.color,
        "parent_id": payload.parent_id,
        "position": await _next_position(
            auth,
            TABLES["folders"],
            parent_id=payload.parent_id,
        ),
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
    if "parent_id" in updates:
        parents = await _folder_parent_map(auth)
        parent_id = updates["parent_id"]
        if not isinstance(parent_id, str) and parent_id is not None:
            raise ApiError(422, "folder_parent_invalid", "Folder parent is invalid")
        _validate_folder_parent(folder_id, parent_id, parents)
        if parent_id != parents[folder_id] and "position" not in updates:
            updates["position"] = await _next_position(
                auth,
                TABLES["folders"],
                parent_id=parent_id,
            )
    updates["updated_at"] = _now()
    rows = await _execute(
        auth.client.table(TABLES["folders"])
        .update(updates)
        .eq("id", folder_id)
        .eq("user_id", auth.user.id)
        .select("*")
    )
    return FolderOut(**_ensure_row(rows, "Folder"))


async def delete_folder(
    folder_id: str,
    auth: AuthContext,
    destination_folder_id: str | None = None,
) -> None:
    if destination_folder_id == folder_id:
        raise ApiError(
            422,
            "folder_destination_invalid",
            "A folder cannot be its own deletion destination",
        )
    rows = await _execute(
        auth.client.rpc(
            "delete_folder",
            {
                "p_folder_id": folder_id,
                "p_destination_folder_id": destination_folder_id,
                "p_user_id": auth.user.id,
            },
        )
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
        "color": payload.color,
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
    destination_folder_id = updates.pop("folder_id", None)

    if "folder_id" in payload.model_fields_set:
        if not isinstance(destination_folder_id, str) or not destination_folder_id:
            raise ApiError(422, "section_folder_invalid", "Section folder is invalid")
        rows = await _execute(
            auth.client.rpc(
                "move_section",
                {
                    "p_section_id": section_id,
                    "p_destination_folder_id": destination_folder_id,
                    "p_user_id": auth.user.id,
                    "p_name": updates.get("name"),
                    "p_color": updates.get("color"),
                    "p_update_name": "name" in updates,
                    "p_update_color": "color" in updates,
                },
            )
        )
        return SectionOut(**_ensure_row(rows, "Section"))

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
