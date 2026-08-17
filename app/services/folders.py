from typing import Any
from uuid import uuid4

from app.core.errors import ApiError
from app.integrations.supabase import AuthContext
from app.schemas import (
    FolderCreate,
    FolderOut,
    FolderTreeOut,
    FolderUpdate,
    PositionUpdate,
)
from app.services._db import TABLES, ensure_row, execute, next_position, now, reorder


async def list_folders(auth: AuthContext) -> list[FolderOut]:
    rows = await execute(
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


async def folder_parent_map(auth: AuthContext) -> dict[str, str | None]:
    rows = await execute(
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


def validate_folder_parent(
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
        validate_folder_parent(
            None,
            payload.parent_id,
            await folder_parent_map(auth),
        )
    timestamp = now()
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "name": payload.name,
        "color": payload.color,
        "parent_id": payload.parent_id,
        "position": await next_position(
            auth,
            TABLES["folders"],
            parent_id=payload.parent_id,
        ),
        "created_at": timestamp,
        "updated_at": timestamp,
        "user_id": auth.user.id,
    }
    rows = await execute(auth.client.table(TABLES["folders"]).insert(row).select("*"))
    return FolderOut(**ensure_row(rows, "Folder"))


async def update_folder(
    folder_id: str,
    payload: FolderUpdate,
    auth: AuthContext,
) -> FolderOut:
    updates = payload.model_dump(by_alias=False, exclude_unset=True)
    if "parent_id" in updates:
        parents = await folder_parent_map(auth)
        parent_id = updates["parent_id"]
        if not isinstance(parent_id, str) and parent_id is not None:
            raise ApiError(422, "folder_parent_invalid", "Folder parent is invalid")
        validate_folder_parent(folder_id, parent_id, parents)
        if parent_id != parents[folder_id] and "position" not in updates:
            updates["position"] = await next_position(
                auth,
                TABLES["folders"],
                parent_id=parent_id,
            )
    updates["updated_at"] = now()
    rows = await execute(
        auth.client.table(TABLES["folders"])
        .update(updates)
        .eq("id", folder_id)
        .eq("user_id", auth.user.id)
        .select("*")
    )
    return FolderOut(**ensure_row(rows, "Folder"))


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
    rows = await execute(
        auth.client.rpc(
            "delete_folder",
            {
                "p_folder_id": folder_id,
                "p_destination_folder_id": destination_folder_id,
                "p_user_id": auth.user.id,
            },
        )
    )
    ensure_row(rows, "Folder")


async def reorder_folders(
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    await reorder(TABLES["folders"], payload, auth)
