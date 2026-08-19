from typing import Any
from uuid import uuid4

from app.integrations.supabase import AuthContext
from app.schemas import PositionUpdate, SectionCreate, SectionOut, SectionUpdate
from app.services._db import TABLES, ensure_row, execute, next_position, now, reorder


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
        "position": await next_position(auth, TABLES["sections"]),
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
    updates = payload.model_dump(by_alias=False, exclude_unset=True)
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
