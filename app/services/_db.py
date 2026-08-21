from datetime import UTC, datetime
from typing import Any

import httpx
from postgrest.exceptions import APIError

from app.core.errors import ApiError
from app.integrations.supabase import AuthContext
from app.schemas import PositionUpdate

TABLES = {
    "bookmarks": "items",
    "folders": "folders",
    "sections": "sections",
    "folder_sections": "folder_sections",
}
RESOURCE_NAMES = {
    TABLES["bookmarks"]: "Bookmark",
    TABLES["folders"]: "Folder",
    TABLES["sections"]: "Section",
    TABLES["folder_sections"]: "Folder section",
}


def now() -> str:
    return datetime.now(UTC).isoformat()


async def execute(query: Any) -> list[dict[str, Any]]:
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


def ensure_row(
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


async def next_position(
    auth: AuthContext,
    table: str,
    **filters: object,
) -> int:
    query = auth.client.table(table).select("position").eq("user_id", auth.user.id)
    for column, value in filters.items():
        query = query.is_(column, "null") if value is None else query.eq(column, value)
    rows = await execute(query.order("position", desc=True).limit(1))
    if not rows:
        return 0
    position = rows[0].get("position")
    return (
        position + 1
        if isinstance(position, int) and not isinstance(position, bool)
        else 0
    )


async def reorder(
    table: str,
    payload: list[PositionUpdate],
    auth: AuthContext,
) -> None:
    timestamp = now()
    for item in payload:
        rows = await execute(
            auth.client.table(table)
            .update({"position": item.position, "updated_at": timestamp})
            .eq("id", item.id)
            .eq("user_id", auth.user.id)
            .select("id")
        )
        ensure_row(rows, RESOURCE_NAMES[table])
