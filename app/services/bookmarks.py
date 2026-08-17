from typing import Any
from uuid import uuid4

from app.integrations.supabase import AuthContext
from app.schemas import BookmarkCreate, BookmarkOut, BookmarkUpdate, PositionUpdate
from app.services.db import TABLES, ensure_row, execute, next_position, now, reorder
from app.services.folders import (
    create_folder,
    delete_folder,
    list_folder_tree,
    list_folders,
    reorder_folders,
    update_folder,
)
from app.services.sections import (
    create_section,
    delete_section,
    list_sections,
    reorder_sections,
    update_section,
)

__all__ = [
    "create_bookmark",
    "create_folder",
    "create_section",
    "delete_bookmark",
    "delete_folder",
    "delete_section",
    "list_bookmarks",
    "list_folder_tree",
    "list_folders",
    "list_sections",
    "reorder_bookmarks",
    "reorder_folders",
    "reorder_sections",
    "update_bookmark",
    "update_folder",
    "update_section",
]


async def list_bookmarks(auth: AuthContext) -> list[BookmarkOut]:
    rows = await execute(
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
    timestamp = now()
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "title": payload.title,
        "url": payload.url,
        "description": payload.description,
        "is_favorite": payload.is_favorite,
        "folder_id": payload.folder_id,
        "section_id": payload.section_id,
        "position": await next_position(auth, TABLES["bookmarks"]),
        "created_at": timestamp,
        "updated_at": timestamp,
        "user_id": auth.user.id,
    }
    rows = await execute(auth.client.table(TABLES["bookmarks"]).insert(row).select("*"))
    return BookmarkOut(**ensure_row(rows, "Bookmark"))


async def update_bookmark(
    bookmark_id: str,
    payload: BookmarkUpdate,
    auth: AuthContext,
) -> BookmarkOut:
    updates = payload.model_dump(by_alias=False, exclude_unset=True)
    updates["updated_at"] = now()
    rows = await execute(
        auth.client.table(TABLES["bookmarks"])
        .update(updates)
        .eq("id", bookmark_id)
        .eq("user_id", auth.user.id)
        .select("*")
    )
    return BookmarkOut(**ensure_row(rows, "Bookmark"))


async def delete_bookmark(bookmark_id: str, auth: AuthContext) -> None:
    rows = await execute(
        auth.client.table(TABLES["bookmarks"])
        .delete()
        .eq("id", bookmark_id)
        .eq("user_id", auth.user.id)
        .select("id")
    )
    ensure_row(rows, "Bookmark")


async def reorder_bookmarks(
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    await reorder(TABLES["bookmarks"], payload, auth)
