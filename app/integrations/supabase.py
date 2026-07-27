from collections.abc import AsyncIterator
from dataclasses import dataclass
from secrets import compare_digest
from typing import Annotated

import httpx
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest.exceptions import APIError as PostgrestAPIError
from supabase_auth.errors import AuthApiError, AuthRetryableError, AuthUnknownError
from supabase_auth.types import User

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from supabase import AsyncClient, AsyncClientOptions, acreate_client

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ServiceUser:
    id: str
    email: None = None


@dataclass(frozen=True)
class AuthContext:
    user: User | ServiceUser
    client: AsyncClient


async def _get_service_user(client: AsyncClient) -> ServiceUser:
    tables = ("folders", "sections", "items")
    owner_id: str | None = None
    try:
        for table in tables:
            response = await client.table(table).select("user_id").limit(1).execute()
            rows = response.data
            if not isinstance(rows, list):
                raise TypeError("invalid owner response")
            if rows:
                first = rows[0]
                if not isinstance(first, dict):
                    raise TypeError("invalid owner row")
                value = first.get("user_id")
                if not isinstance(value, str) or not value:
                    raise ValueError("invalid owner value")
                owner_id = value
                break

        if owner_id is None:
            raise ApiError(
                503,
                "service_identity_unavailable",
                "Service identity is unavailable",
            )

        for table in tables:
            response = (
                await client.table(table)
                .select("user_id")
                .neq("user_id", owner_id)
                .limit(1)
                .execute()
            )
            rows = response.data
            if not isinstance(rows, list):
                raise TypeError("invalid owner response")
            if rows:
                raise ApiError(
                    503,
                    "service_identity_unavailable",
                    "Service identity is unavailable",
                )
    except ApiError:
        raise
    except (PostgrestAPIError, httpx.HTTPError, TypeError, ValueError) as error:
        raise ApiError(
            503,
            "service_identity_unavailable",
            "Service identity is unavailable",
        ) from error

    return ServiceUser(id=owner_id)


async def _new_client(
    settings: Settings, key: str
) -> tuple[AsyncClient, httpx.AsyncClient]:
    http_client = httpx.AsyncClient(timeout=settings.SUPABASE_TIMEOUT_SECONDS)
    try:
        client = await acreate_client(
            str(settings.SUPABASE_URL),
            key,
            options=AsyncClientOptions(
                schema=settings.supabase_schema,
                persist_session=False,
                auto_refresh_token=False,
                postgrest_client_timeout=settings.SUPABASE_TIMEOUT_SECONDS,
                httpx_client=http_client,
            ),
        )
    except Exception:
        await http_client.aclose()
        raise
    return client, http_client


async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[AuthContext]:
    if credentials is None:
        raise ApiError(401, "authentication_required", "Bearer token is required")

    client, http_client = await _new_client(
        settings, settings.SUPABASE_PUBLISHABLE_KEY.get_secret_value()
    )
    try:
        try:
            response = await client.auth.get_user(credentials.credentials)
        except AuthApiError as error:
            if error.status in (401, 403) or (
                error.status == 400 and error.code in {"bad_jwt", "invalid_jwt"}
            ):
                raise ApiError(
                    401, "invalid_access_token", "Invalid access token"
                ) from error
            raise ApiError(
                503,
                "authentication_service_unavailable",
                "Authentication service is unavailable",
            ) from error
        except (AuthRetryableError, AuthUnknownError, httpx.HTTPError) as error:
            raise ApiError(
                503,
                "authentication_service_unavailable",
                "Authentication service is unavailable",
            ) from error

        if response is None:
            raise ApiError(401, "invalid_access_token", "Invalid access token")

        client.postgrest.auth(credentials.credentials)
        yield AuthContext(user=response.user, client=client)
    finally:
        await http_client.aclose()


async def get_resource_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    service_key: Annotated[str | None, Header(alias="X-Bookmark-Key")] = None,
) -> AsyncIterator[AuthContext]:
    if service_key is not None:
        configured_key = settings.BOOKMARK_API_KEY
        if configured_key is None or not compare_digest(
            service_key,
            configured_key.get_secret_value(),
        ):
            raise ApiError(401, "invalid_api_key", "Invalid API key")

        async for client in get_admin_client(settings):
            yield AuthContext(user=await _get_service_user(client), client=client)
        return

    async for context in get_auth_context(credentials, settings):
        yield context


async def get_admin_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[AsyncClient]:
    if settings.SUPABASE_SECRET_KEY is None:
        raise ApiError(
            503,
            "administrator_client_unavailable",
            "Administrator client is unavailable",
        )

    client, http_client = await _new_client(
        settings, settings.SUPABASE_SECRET_KEY.get_secret_value()
    )
    try:
        yield client
    finally:
        await http_client.aclose()
