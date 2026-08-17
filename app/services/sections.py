from typing import Any
from uuid import uuid4

from app.core.errors import ApiError
from app.integrations.supabase import AuthContext
from app.schemas import PositionUpdate, SectionCreate, SectionOut, SectionUpdate
from app.services.db import TABLES, ensure_row, execute, next_position, now, reorder


async def list_sections(auth: AuthContext) -> list[SectionOut]:
    rows = await execute(
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
    timestamp = now()
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "name": payload.name,
        "color": payload.color,
        "folder_id": payload.folder_id,
        "position": await next_position(
            auth,
            TABLES["sections"],
            folder_id=payload.folder_id,
        ),
        "created_at": timestamp,
        "updated_at": timestamp,
        "user_id": auth.user.id,
    }
    rows = await execute(auth.client.table(TABLES["sections"]).insert(row).select("*"))
    return SectionOut(**ensure_row(rows, "Section"))


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
        rows = await execute(
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
        return SectionOut(**ensure_row(rows, "Section"))

    updates["updated_at"] = now()
    rows = await execute(
        auth.client.table(TABLES["sections"])
        .update(updates)
        .eq("id", section_id)
        .eq("user_id", auth.user.id)
        .select("*")
    )
    return SectionOut(**ensure_row(rows, "Section"))


async def delete_section(section_id: str, auth: AuthContext) -> None:
    rows = await execute(
        auth.client.table(TABLES["sections"])
        .delete()
        .eq("id", section_id)
        .eq("user_id", auth.user.id)
        .select("id")
    )
    ensure_row(rows, "Section")


async def reorder_sections(
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    await reorder(TABLES["sections"], payload, auth)
