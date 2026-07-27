from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.integrations.supabase import AuthContext, get_resource_auth_context
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
from app.services import bookmarks

router = APIRouter(prefix="/api", tags=["bookmarks"])
AuthDependency = Annotated[AuthContext, Depends(get_resource_auth_context)]


@router.get("/bookmarks", response_model=list[BookmarkOut])
async def list_bookmarks(auth: AuthDependency) -> list[BookmarkOut]:
    return await bookmarks.list_bookmarks(auth)


@router.post(
    "/bookmarks",
    response_model=BookmarkOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_bookmark(
    payload: BookmarkCreate,
    auth: AuthDependency,
) -> BookmarkOut:
    return await bookmarks.create_bookmark(payload, auth)


@router.patch("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def update_bookmark(
    bookmark_id: str,
    payload: BookmarkUpdate,
    auth: AuthDependency,
) -> BookmarkOut:
    return await bookmarks.update_bookmark(bookmark_id, payload, auth)


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: str, auth: AuthDependency) -> None:
    await bookmarks.delete_bookmark(bookmark_id, auth)


@router.post("/bookmarks/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_bookmarks(
    payload: list[PositionUpdate],
    auth: AuthDependency,
) -> None:
    await bookmarks.reorder_bookmarks(payload, auth)


@router.get("/folders", response_model=list[FolderOut])
async def list_folders(auth: AuthDependency) -> list[FolderOut]:
    return await bookmarks.list_folders(auth)


@router.post(
    "/folders",
    response_model=FolderOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    payload: FolderCreate,
    auth: AuthDependency,
) -> FolderOut:
    return await bookmarks.create_folder(payload, auth)


@router.patch("/folders/{folder_id}", response_model=FolderOut)
async def update_folder(
    folder_id: str,
    payload: FolderUpdate,
    auth: AuthDependency,
) -> FolderOut:
    return await bookmarks.update_folder(folder_id, payload, auth)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(folder_id: str, auth: AuthDependency) -> None:
    await bookmarks.delete_folder(folder_id, auth)


@router.post("/folders/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_folders(
    payload: list[PositionUpdate],
    auth: AuthDependency,
) -> None:
    await bookmarks.reorder_folders(payload, auth)


@router.get("/sections", response_model=list[SectionOut])
async def list_sections(auth: AuthDependency) -> list[SectionOut]:
    return await bookmarks.list_sections(auth)


@router.post(
    "/sections",
    response_model=SectionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_section(
    payload: SectionCreate,
    auth: AuthDependency,
) -> SectionOut:
    return await bookmarks.create_section(payload, auth)


@router.patch("/sections/{section_id}", response_model=SectionOut)
async def update_section(
    section_id: str,
    payload: SectionUpdate,
    auth: AuthDependency,
) -> SectionOut:
    return await bookmarks.update_section(section_id, payload, auth)


@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(section_id: str, auth: AuthDependency) -> None:
    await bookmarks.delete_section(section_id, auth)


@router.post("/sections/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_sections(
    payload: list[PositionUpdate],
    auth: AuthDependency,
) -> None:
    await bookmarks.reorder_sections(payload, auth)
